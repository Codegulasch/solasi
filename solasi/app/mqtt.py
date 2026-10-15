"""MQTT-Anbindung: echte Home-Assistant-Entitäten per MQTT-Discovery.

Enthält einen kleinen, abhängigkeitsfreien MQTT-3.1.1-Client (QoS 0) und die Brücke,
die Messwerte veröffentlicht und Schalter von Home Assistant entgegennimmt.
"""
import asyncio
import json
import logging
import os
import ssl as ssl_lib

import aiohttp

log = logging.getLogger("solasi.mqtt")

SUPERVISOR_URL = os.environ.get("SUPERVISOR_URL", "http://supervisor")


# ----------------------------------------------------------------------------
# Minimaler MQTT-Client
# ----------------------------------------------------------------------------
def _enc_len(n):
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _str(s):
    b = s.encode("utf-8") if isinstance(s, str) else s
    return len(b).to_bytes(2, "big") + b


def packet(first, body):
    return bytes([first]) + _enc_len(len(body)) + body


class MqttError(Exception):
    pass


class MqttClient:
    def __init__(self, host, port=1883, user="", password="", client_id="solasi", keepalive=30,
                 will=None, use_ssl=False, on_message=None):
        self.host, self.port, self.user, self.password = host, int(port), user, password
        self.client_id, self.keepalive = client_id, keepalive
        self.will = will                       # (topic, payload, retain)
        self.use_ssl = use_ssl
        self.on_message = on_message
        self._r = self._w = None
        self._tasks = []
        self.connected = False
        self.closed = asyncio.Event()

    async def connect(self, timeout=10):
        ctx = None
        if self.use_ssl:
            ctx = ssl_lib.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl_lib.CERT_NONE
        self._r, self._w = await asyncio.wait_for(asyncio.open_connection(self.host, self.port, ssl=ctx), timeout)
        flags = 0x02                                              # saubere Sitzung
        body = _str("MQTT") + bytes([4])
        payload = _str(self.client_id)
        if self.will:
            flags |= 0x04 | (0x20 if self.will[2] else 0)
            payload += _str(self.will[0]) + _str(self.will[1])
        if self.user:
            flags |= 0x80
            payload += _str(self.user)
            if self.password:
                flags |= 0x40
                payload += _str(self.password)
        body += bytes([flags]) + self.keepalive.to_bytes(2, "big") + payload
        self._w.write(packet(0x10, body))
        await self._w.drain()
        first, data = await asyncio.wait_for(self._read_packet(), timeout)
        if first >> 4 != 2 or len(data) < 2:
            raise MqttError("Unerwartete Antwort des Brokers")
        if data[1] != 0:
            raise MqttError({1: "Protokoll abgelehnt", 2: "Client-ID abgelehnt", 3: "Broker nicht verfügbar",
                             4: "Benutzer oder Passwort falsch", 5: "Nicht autorisiert"}.get(data[1], f"Fehler {data[1]}"))
        self.connected = True
        self._tasks = [asyncio.create_task(self._reader()), asyncio.create_task(self._pinger())]

    async def _read_packet(self):
        first = (await self._r.readexactly(1))[0]
        mult, length = 1, 0
        while True:
            b = (await self._r.readexactly(1))[0]
            length += (b & 0x7F) * mult
            mult *= 128
            if not b & 0x80:
                break
            if mult > 128 ** 3:
                raise MqttError("Ungültige Paketlänge")
        return first, (await self._r.readexactly(length)) if length else b""

    async def _reader(self):
        try:
            while True:
                first, data = await self._read_packet()
                if first >> 4 == 3:                               # PUBLISH
                    n = int.from_bytes(data[:2], "big")
                    topic = data[2:2 + n].decode("utf-8", "replace")
                    pos = 2 + n
                    if (first >> 1) & 3:
                        pos += 2
                    if self.on_message:
                        try:
                            res = self.on_message(topic, data[pos:].decode("utf-8", "replace"))
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception:  # noqa: BLE001
                            log.exception("Fehler bei MQTT-Nachricht auf %s", topic)
        except (asyncio.IncompleteReadError, ConnectionError, OSError, MqttError):
            pass
        finally:
            self.connected = False
            self.closed.set()

    async def _pinger(self):
        try:
            while self.connected:
                await asyncio.sleep(self.keepalive / 2)
                self._w.write(b"\xc0\x00")
                await self._w.drain()
        except (ConnectionError, OSError):
            self.connected = False
            self.closed.set()

    async def publish(self, topic, payload, retain=False):
        if not self.connected:
            raise MqttError("nicht verbunden")
        data = payload if isinstance(payload, (bytes, bytearray)) else str(payload).encode("utf-8")
        self._w.write(packet(0x30 | (1 if retain else 0), _str(topic) + data))
        await self._w.drain()

    async def subscribe(self, topic):
        if not self.connected:
            raise MqttError("nicht verbunden")
        self._w.write(packet(0x82, (1).to_bytes(2, "big") + _str(topic) + b"\x00"))
        await self._w.drain()

    async def close(self, clean=True):
        was = self.connected
        self.connected = False
        for t in self._tasks:
            t.cancel()
        if self._w is not None:
            try:
                if was and clean:
                    self._w.write(b"\xe0\x00")
                    await self._w.drain()
                self._w.close()
            except Exception:  # noqa: BLE001
                pass
        self.closed.set()


# ----------------------------------------------------------------------------
# Entitäten
# ----------------------------------------------------------------------------
# (Schlüssel, Name, Einheit, device_class, state_class, Symbol)
POWER = (
    ("pv_w", "Solarleistung", "mdi:solar-power"),
    ("house_w", "Hausverbrauch", "mdi:home-lightning-bolt"),
    ("battery_w", "Speicherleistung", "mdi:battery-charging"),
    ("grid_w", "Netzleistung", "mdi:transmission-tower"),
    ("target_w", "Sollwert", "mdi:target"),
    ("surplus_w", "Überschuss", "mdi:flash"),
    ("base_w", "Grundlast (gelernt)", "mdi:home-clock"),
)
ENERGY = (
    ("e_pv", "pv", "Solarertrag gesamt", "mdi:solar-power"),
    ("e_house", "house", "Hausverbrauch gesamt", "mdi:home-lightning-bolt"),
    ("e_imp", "imp", "Netzbezug gesamt", "mdi:transmission-tower-export"),
    ("e_exp", "exp", "Einspeisung gesamt", "mdi:transmission-tower-import"),
    ("e_bat_chg", "bat_chg", "Speicher geladen gesamt", "mdi:battery-arrow-up"),
    ("e_bat_dis", "bat_dis", "Speicher entladen gesamt", "mdi:battery-arrow-down"),
)
SWITCHES = (
    ("control", "Regelung", "mdi:power"),
    ("test", "Testmodus", "mdi:flask-outline"),
    ("stop", "Not-Aus", "mdi:alert-octagon"),
)


class MqttBridge:
    """Veröffentlicht Messwerte als MQTT-Entitäten und setzt Befehle aus Home Assistant um."""

    def __init__(self, ctrl, version="dev"):
        self.ctrl = ctrl
        self.version = version
        self.client = None
        self.status = {"state": "aus", "detail": "", "host": ""}
        self._sent = {}
        self._task = None
        self._stop = False
        self.retry_s = 15

    # ---------- Konfiguration ----------
    @property
    def cfg(self):
        return self.ctrl.cfg.get("mqtt", {})

    @property
    def prefix(self):
        return (self.cfg.get("prefix") or "solasi").strip("/ ") or "solasi"

    @property
    def active(self):
        return bool(self.client and self.client.connected)

    async def credentials(self):
        c = self.cfg
        if c.get("host"):
            return {"host": c["host"], "port": int(c.get("port") or 1883), "user": c.get("user", ""),
                    "password": c.get("password", ""), "ssl": bool(c.get("ssl"))}
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            raise MqttError("Kein MQTT-Broker eingetragen und kein Supervisor verfügbar")
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {token}"}) as s:
            async with s.get(f"{SUPERVISOR_URL}/services/mqtt", timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    raise MqttError("Kein MQTT-Broker gefunden (Mosquitto-Add-on installieren oder Broker eintragen)")
                d = (await r.json()).get("data") or {}
        if not d.get("host"):
            raise MqttError("Kein MQTT-Broker gefunden (Mosquitto-Add-on installieren oder Broker eintragen)")
        return {"host": d["host"], "port": int(d.get("port") or 1883), "user": d.get("username", ""),
                "password": d.get("password", ""), "ssl": bool(d.get("ssl"))}

    # ---------- Lebenszyklus ----------
    def start(self):
        if self._task is None:
            self._stop = False
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop = True
        if self.client is not None and self.client.connected:
            try:
                await self.client.publish(f"{self.prefix}/availability", "offline", retain=True)
            except Exception:  # noqa: BLE001
                pass
            await self.client.close()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        self.status = {**self.status, "state": "aus"}

    async def _run(self):
        while not self._stop:
            if not self.cfg.get("enabled", True):
                self.status = {"state": "aus", "detail": "In den Einstellungen ausgeschaltet", "host": ""}
                await asyncio.sleep(5)
                continue
            try:
                cr = await self.credentials()
                if self.status["state"] != "fehler":      # Fehleranzeige bleiben lassen, bis es klappt
                    self.status = {"state": "verbinde", "detail": "", "host": cr["host"]}
                self.client = MqttClient(
                    cr["host"], cr["port"], cr["user"], cr["password"], client_id=f"solasi-{os.getpid()}",
                    will=(f"{self.prefix}/availability", "offline", True), use_ssl=cr["ssl"],
                    on_message=self._on_message)
                await self.client.connect()
                await self.client.subscribe(f"{self.prefix}/+/set")
                self._sent.clear()
                await self.client.publish(f"{self.prefix}/availability", "online", retain=True)
                await self._discovery()
                self.status = {"state": "verbunden", "detail": "", "host": cr["host"]}
                self.ctrl.event("info", f"MQTT verbunden ({cr['host']}): SOLASI-Entitäten sind angelegt")
                await self.publish_state()
                await self.client.closed.wait()
                if not self._stop:
                    self.ctrl.event("error", "MQTT-Verbindung verloren – neuer Versuch")
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                msg = str(e) or e.__class__.__name__
                if self.status.get("detail") != msg:
                    self.ctrl.event("info", f"MQTT nicht verfügbar: {msg}")
                self.status = {"state": "fehler", "detail": msg, "host": self.status.get("host", "")}
            finally:
                if self.client is not None:
                    await self.client.close(clean=False)
            if not self._stop:
                await asyncio.sleep(self.retry_s)

    # ---------- Discovery ----------
    def _device(self):
        return {"identifiers": ["solasi"], "name": "SOLASI", "manufacturer": "SOLASI", "model": "Add-on",
                "sw_version": self.version}

    def discovery_messages(self):
        p = self.prefix
        base = {"availability_topic": f"{p}/availability", "device": self._device(), "has_entity_name": True}
        out = {}

        def add(domain, key, cfg):
            out[f"homeassistant/{domain}/solasi/{key}/config"] = {**base, "unique_id": f"solasi_{key}", **cfg}

        for key, name, icon in POWER:
            add("sensor", key, {"name": name, "icon": icon, "state_topic": f"{p}/{key}",
                                "unit_of_measurement": "W", "device_class": "power", "state_class": "measurement"})
        add("sensor", "soc", {"name": "Ladestand Ø", "state_topic": f"{p}/soc", "unit_of_measurement": "%",
                              "device_class": "battery", "state_class": "measurement"})
        add("sensor", "state", {"name": "Zustand", "icon": "mdi:solar-power", "state_topic": f"{p}/state",
                                "json_attributes_topic": f"{p}/attributes"})
        for key, _src, name, icon in ENERGY:
            add("sensor", key, {"name": name, "icon": icon, "state_topic": f"{p}/{key}",
                                "unit_of_measurement": "kWh", "device_class": "energy",
                                "state_class": "total_increasing", "suggested_display_precision": 2})
        add("binary_sensor", "meter_problem", {"name": "Zählerproblem", "device_class": "problem",
                                               "state_topic": f"{p}/meter_problem", "payload_on": "ON", "payload_off": "OFF"})
        add("binary_sensor", "eco", {"name": "Eco-Modus aktiv", "icon": "mdi:leaf", "state_topic": f"{p}/eco",
                                     "payload_on": "ON", "payload_off": "OFF"})
        for key, name, icon in SWITCHES:
            add("switch", key, {"name": name, "icon": icon, "state_topic": f"{p}/{key}",
                                "command_topic": f"{p}/{key}/set", "payload_on": "ON", "payload_off": "OFF"})
        return out

    async def _discovery(self):
        for topic, cfg in self.discovery_messages().items():
            await self.client.publish(topic, json.dumps(cfg, ensure_ascii=False), retain=True)

    async def remove_discovery(self):
        """Löscht alle SOLASI-Entitäten wieder aus Home Assistant."""
        if not self.active:
            return
        for topic in self.discovery_messages():
            await self.client.publish(topic, b"", retain=True)

    # ---------- Zustände ----------
    def values(self):
        c = self.ctrl
        st = c.status
        if not st:
            return {}
        stopped = st.get("safety", {}).get("state") == "stopped"
        cfg = c.cfg
        v = {
            "pv_w": st.get("pv_w"), "house_w": st.get("house_w"), "battery_w": st.get("bat_w"),
            "grid_w": st.get("grid_w"), "target_w": st.get("t_target"), "surplus_w": st.get("surplus_w"),
            "base_w": st.get("learned_base_load"), "soc": st.get("avg_soc"),
            "meter_problem": "ON" if st.get("meter_ok") is False else "OFF",
            "eco": "ON" if st.get("eco_active") else "OFF",
            "control": "ON" if cfg["enabled"] else "OFF",
            "test": "ON" if cfg["dry_run"] else "OFF",
            "stop": "ON" if stopped else "OFF",
        }
        for key, src, _n, _i in ENERGY:
            v[key] = round(c.stats.totals.get(src, 0.0) / 1000.0, 3)
        return v

    async def publish_state(self):
        if not self.active:
            return
        c = self.ctrl
        p = self.prefix
        payloads = {}
        for k, val in self.values().items():
            payloads[f"{p}/{k}"] = "None" if val is None else str(val)
        main = c._entity_payloads().get("sensor.solasi")
        if main:
            payloads[f"{p}/state"] = str(main[0])
            payloads[f"{p}/attributes"] = json.dumps(main[1], default=str, ensure_ascii=False)
        for topic, payload in payloads.items():
            if self._sent.get(topic) == payload:
                continue
            try:
                await self.client.publish(topic, payload, retain=True)
            except Exception as e:  # noqa: BLE001
                log.debug("MQTT-Veröffentlichung fehlgeschlagen: %s", e)
                return
            self._sent[topic] = payload

    # ---------- Befehle ----------
    async def _on_message(self, topic, payload):
        p = self.prefix + "/"
        if not (topic.startswith(p) and topic.endswith("/set")):
            return
        key = topic[len(p):-4]
        on = payload.strip().upper() in ("ON", "TRUE", "1")
        c = self.ctrl
        if key == "control":
            await c.apply_settings({"enabled": on}, source="MQTT")
        elif key == "test":
            await c.apply_settings({"dry_run": on}, source="MQTT")
        elif key == "stop":
            if on:
                await c.kill("Über Home Assistant gestoppt", "mqtt")
            else:
                c.resume()
        else:
            return
        self._sent.pop(f"{self.prefix}/{key}", None)      # Rückmeldung sicher senden
        await self.publish_state()
