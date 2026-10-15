"""Minimaler Home-Assistant-WebSocket-Client mit Zustandscache."""
import asyncio
import logging
import math
import time
from datetime import datetime, timezone

import aiohttp

log = logging.getLogger("solasi.ha")


def is_num(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def num(x, default=0.0):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _parse_ts(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


class HA:
    def __init__(self, url, token, on_entity_event=None, api_url=None, on_connected=None):
        self.url = url
        self.token = token
        self.on_entity_event = on_entity_event
        self.on_connected = on_connected
        self.api_url = (api_url or "").rstrip("/")
        self._http = None
        self.states = {}  # entity_id -> state dict
        self.seen = {}  # entity_id -> monotonic time der letzten Meldung
        self.connected = False
        self.refresh_interval = 20
        self.timezone = None
        self._ws = None
        self._id = 0
        self._pending = {}

    # ---------- Lesezugriff ----------
    def state(self, eid):
        s = self.states.get(eid)
        return None if s is None else s.get("state")

    def attr(self, eid, name, default=None):
        s = self.states.get(eid)
        if not s:
            return default
        return (s.get("attributes") or {}).get(name, default)

    def age_seen(self, eid):
        t = self.seen.get(eid)
        return float("inf") if t is None else time.monotonic() - t

    def age_changed(self, eid):
        s = self.states.get(eid)
        dt = _parse_ts(s.get("last_changed")) if s else None
        if dt is None:
            return float("inf")
        return (datetime.now(timezone.utc) - dt).total_seconds()

    def device_sensors(self, entity):
        """Sensoren, die vermutlich zum selben Gerät gehören, mit Wert und Einheit.

        Ein Gerät erkennt man am gemeinsamen Anfang der Entitäts-IDs (z. B. anker_solix_solarbank_4_e5000_pro_883_…).
        Gesucht wird das längste Präfix der gewählten Entität, das auch mehrere andere Entitäten haben."""
        obj = (entity or "").partition(".")[2]
        toks = obj.split("_")
        if len(toks) < 3:
            return []
        parts = {eid: eid.split(".", 1)[1].split("_") for eid in self.states}
        tries = [(k, 2) for k in range(len(toks) - 1, 2, -1)] + [(k, 1) for k in range(len(toks) - 1, 1, -1)]
        for k, minimum in tries:
            group = [eid for eid, t in parts.items() if eid != entity and t[:k] == toks[:k]]
            if len(group) >= minimum:
                out = []
                for eid in group:
                    if eid.startswith("sensor."):
                        st = self.states[eid]
                        attrs = st.get("attributes") or {}
                        out.append({"id": eid, "name": attrs.get("friendly_name", ""), "state": st.get("state"),
                                    "unit": attrs.get("unit_of_measurement", "")})
                return sorted(out, key=lambda e: e["id"])
        return []

    def entities(self):
        out = []
        for eid, s in self.states.items():
            out.append({
                "id": eid,
                "name": (s.get("attributes") or {}).get("friendly_name", ""),
                "domain": eid.split(".", 1)[0],
                "state": s.get("state"),
                "unit": (s.get("attributes") or {}).get("unit_of_measurement", ""),
            })
        return sorted(out, key=lambda e: e["id"])

    # ---------- Verbindung ----------
    async def run(self):
        backoff = 2
        while True:
            try:
                await self._session()
                backoff = 2
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                log.warning("Verbindung zu Home Assistant verloren: %s", e)
            self.connected = False
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("Verbindung getrennt"))
            self._pending.clear()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

    async def _session(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.ws_connect(self.url, heartbeat=30) as ws:
                msg = await ws.receive_json()
                if msg.get("type") != "auth_required":
                    raise ConnectionError(f"Unerwartet: {msg}")
                await ws.send_json({"type": "auth", "access_token": self.token})
                msg = await ws.receive_json()
                if msg.get("type") != "auth_ok":
                    raise ConnectionError(f"Anmeldung fehlgeschlagen: {msg}")
                self._ws = ws
                reader = asyncio.create_task(self._reader(ws))
                try:
                    res = await self.call({"type": "get_states"})
                    now = time.monotonic()
                    self.states = {s["entity_id"]: s for s in res}
                    self.seen = {eid: now for eid in self.states}
                    await self.call({"type": "subscribe_events", "event_type": "state_changed"})
                    try:
                        await self.call({"type": "subscribe_events", "event_type": "state_reported"})
                    except Exception:  # noqa: BLE001
                        log.info("state_reported nicht verfügbar (ältere HA-Version)")
                    try:
                        cfg = await self.call({"type": "get_config"}, timeout=5)
                        self.timezone = (cfg or {}).get("time_zone")
                        from util import set_timezone
                        set_timezone(self.timezone)
                    except Exception:  # noqa: BLE001
                        log.info("Zeitzone nicht ermittelbar, es wird UTC verwendet")
                    self.connected = True
                    log.info("Mit Home Assistant verbunden (%d Entitäten)", len(self.states))
                    if self.on_connected:
                        asyncio.create_task(self.on_connected())
                    refresher = asyncio.create_task(self._refresher())
                    try:
                        await reader
                    finally:
                        refresher.cancel()
                finally:
                    reader.cancel()
                    self._ws = None

    async def _refresher(self):
        """Gleicht den Cache regelmäßig ab. Merkt auch Sensoren, deren Wert unverändert bleibt
        (nur last_reported ändert sich), damit sie nicht fälschlich als ausgefallen gelten."""
        while True:
            await asyncio.sleep(self.refresh_interval)
            try:
                res = await self.call({"type": "get_states"})
            except Exception as e:  # noqa: BLE001
                log.debug("Abgleich fehlgeschlagen: %s", e)
                continue
            now = time.monotonic()
            new = {s["entity_id"]: s for s in res}
            for eid, st in new.items():
                old = self.states.get(eid)
                if (old is None or old.get("last_reported") != st.get("last_reported")
                        or old.get("last_updated") != st.get("last_updated")):
                    self.seen[eid] = now
            self.states = new

    async def _reader(self, ws):
        async for m in ws:
            if m.type != aiohttp.WSMsgType.TEXT:
                if m.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
                continue
            msg = m.json()
            t = msg.get("type")
            if t == "result":
                fut = self._pending.pop(msg.get("id"), None)
                if fut and not fut.done():
                    if msg.get("success"):
                        fut.set_result(msg.get("result"))
                    else:
                        fut.set_exception(RuntimeError(str(msg.get("error"))))
            elif t == "event":
                self._handle_event(msg.get("event") or {})

    def _handle_event(self, ev):
        data = ev.get("data") or {}
        eid = data.get("entity_id")
        if not eid:
            return
        new = data.get("new_state")
        if new is None:
            if ev.get("event_type") == "state_changed":
                self.states.pop(eid, None)
        else:
            self.states[eid] = new
        self.seen[eid] = time.monotonic()
        if self.on_entity_event:
            self.on_entity_event(eid)

    # ---------- Befehle ----------
    async def call(self, payload, timeout=15):
        if self._ws is None:
            raise ConnectionError("nicht verbunden")
        self._id += 1
        mid = self._id
        fut = asyncio.get_running_loop().create_future()
        self._pending[mid] = fut
        await self._ws.send_json({**payload, "id": mid})
        return await asyncio.wait_for(fut, timeout)

    async def call_service(self, domain, service, data):
        return await self.call({
            "type": "call_service",
            "domain": domain,
            "service": service,
            "service_data": data,
        })

    # ---------- Veröffentlichen von Entitäten (REST) ----------
    async def post_state(self, eid, state, attributes):
        """Setzt den Zustand einer Entität über die Core-REST-API (virtuelle Entität ohne Registry-Eintrag)."""
        if not self.api_url:
            raise RuntimeError("keine API-URL")
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.token}"})
        async with self._http.post(f"{self.api_url}/states/{eid}",
                                   json={"state": str(state), "attributes": attributes}) as r:
            if r.status >= 300:
                raise RuntimeError(f"HTTP {r.status}: {(await r.text())[:120]}")

    async def config_request(self, method, path, body=None):
        """Aufruf der Konfigurations-API von Home Assistant (z. B. config/automation/config/<id>)."""
        if not self.api_url:
            raise RuntimeError("keine API-URL")
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.token}"})
        async with self._http.request(method, f"{self.api_url}/{path}", json=body) as r:
            if r.status >= 300:
                raise RuntimeError(f"HTTP {r.status}")
            try:
                return await r.json()
            except Exception:  # noqa: BLE001
                return None

    async def get_services(self):
        """Liefert {domain: [service, ...]} aller verfügbaren Dienste."""
        res = await self.call({"type": "get_services"})
        return {d: sorted(v.keys()) for d, v in (res or {}).items()}

    async def history(self, entity_ids, start, end):
        """Verlaufsdaten aus dem Recorder (REST) als rohe Antwort."""
        if not self.api_url:
            raise RuntimeError("keine API-URL")
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.token}"})
        params = {"filter_entity_id": ",".join(entity_ids), "end_time": end.isoformat(),
                  "minimal_response": "1", "no_attributes": "1", "significant_changes_only": "0"}
        async with self._http.get(f"{self.api_url}/history/period/{start.isoformat()}", params=params,
                                  timeout=aiohttp.ClientTimeout(total=90)) as r:
            if r.status >= 300:
                raise RuntimeError(f"HTTP {r.status}: {(await r.text())[:120]}")
            return await r.json()

    async def close(self):
        if self._http is not None and not self._http.closed:
            await self._http.close()

    # ---------- Dashboard-Ressource registrieren ----------
    async def ensure_resource(self, base_url, full_url):
        """Trägt die Karte als Dashboard-Ressource ein. Liefert 'exists', 'updated' oder 'created'."""
        res = await self.call({"type": "lovelace/resources"})
        for r in res or []:
            if r.get("url", "").split("?")[0] == base_url:
                if r["url"] == full_url:
                    return "exists"
                await self.call({"type": "lovelace/resources/update", "resource_id": r["id"],
                                 "res_type": "module", "url": full_url})
                return "updated"
        await self.call({"type": "lovelace/resources/create", "res_type": "module", "url": full_url})
        return "created"
