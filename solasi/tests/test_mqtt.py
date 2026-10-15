import asyncio, json, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
from mqtt import MqttClient, MqttError
from stats import Stats
from fake_broker import FakeBroker
from test_integration import start, stop, wait_for


# ---------------- Client ----------------
@pytest.mark.asyncio
async def test_client_verbindet_veroeffentlicht_und_empfaengt():
    b = FakeBroker("u", "p"); await b.start()
    got = []
    c = MqttClient("127.0.0.1", b.port, "u", "p", will=("t/av", "offline", True), on_message=lambda t, p: got.append((t, p)))
    await c.connect()
    await c.subscribe("t/+/set")
    await c.publish("t/x", "hallo", retain=True)
    await b.send("t/a/set", "ON")
    await wait_for(lambda: got and ("t/x", "hallo", True) in b.published)
    assert got == [("t/a/set", "ON")] and b.subs == ["t/+/set"]
    assert b.connects[0]["will"] == ("t/av", "offline") and b.connects[0]["ok"]
    await c.close(); await b.stop()


@pytest.mark.asyncio
async def test_client_falsches_passwort():
    b = FakeBroker("u", "p"); await b.start()
    c = MqttClient("127.0.0.1", b.port, "u", "falsch")
    with pytest.raises(MqttError, match="Passwort"):
        await c.connect()
    await b.stop()


@pytest.mark.asyncio
async def test_client_lange_nachricht():
    b = FakeBroker(); await b.start()
    c = MqttClient("127.0.0.1", b.port)
    await c.connect()
    big = "x" * 40000
    await c.publish("t/big", big)
    await wait_for(lambda: b.published)
    assert b.published[0][1] == big
    await c.close(); await b.stop()


# ---------------- Statistik-Zähler ----------------
def test_gesamtzaehler_wachsen_und_ueberleben_neustart(tmp_path):
    p = str(tmp_path / "s.json")
    st = Stats(p); t = 0.0
    st.update(t, 1000, 500, -500, -500)
    for _ in range(360):
        t += 10; st.update(t, 1000, 500, -500, -500)
    assert round(st.totals["pv"]) == 1000 and round(st.totals["exp"]) == 500
    st.save()
    assert round(Stats(p).totals["pv"]) == 1000
    # Alte Datei ohne Zähler: Summe der Tage
    json.dump({"days": {"2026-01-01": {"pv": 5000.0, "house": 1.0, "imp": 0.0, "exp": 0.0, "bat_dis": 0.0, "bat_chg": 0.0, "secs": 1}}}, open(p, "w"))
    assert Stats(p).totals["pv"] == 5000.0


# ---------------- Brücke ----------------
async def with_bridge(tmp, broker, **mq):
    m, ctrl, ha, tasks = await start(tmp)
    cfg = json.loads(json.dumps(ctrl.cfg))
    cfg["mqtt"].update(host="127.0.0.1", port=broker.port, user="u", password="p", **mq)
    ctrl.store.save(cfg)
    ctrl.mqtt.retry_s = 0.2
    ctrl.mqtt.start()
    return m, ctrl, ha, tasks


@pytest.mark.asyncio
async def test_entitaeten_per_discovery_und_werte(tmp_path):
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b)
    try:
        await wait_for(lambda: "solasi/pv_w" in b.retained and "solasi/e_pv" in b.retained and "solasi/state" in b.retained)
        cfgs = {t: json.loads(p) for t, p in b.retained.items() if t.startswith("homeassistant/")}
        s = cfgs["homeassistant/sensor/solasi/pv_w/config"]
        assert s["device_class"] == "power" and s["state_class"] == "measurement" and s["unit_of_measurement"] == "W"
        assert s["device"]["identifiers"] == ["solasi"] and s["availability_topic"] == "solasi/availability"
        e = cfgs["homeassistant/sensor/solasi/e_imp/config"]
        assert e["device_class"] == "energy" and e["state_class"] == "total_increasing" and e["unit_of_measurement"] == "kWh"
        sw = cfgs["homeassistant/switch/solasi/stop/config"]
        assert sw["command_topic"] == "solasi/stop/set"
        assert b.retained["solasi/availability"] == "online"
        assert b.retained["solasi/control"] == "ON" and b.retained["solasi/test"] == "OFF" and b.retained["solasi/stop"] == "OFF"
        assert b.retained["solasi/grid_w"] == "400"
        assert b.connects[0]["will"] == ("solasi/availability", "offline")
        # Einzelwerte nicht mehr als virtuelle Entitäten
        await asyncio.sleep(0.5)
        assert not any(k.startswith("sensor.solasi_") and k != "sensor.solasi_heartbeat" for k in m.rest)
        assert "sensor.solasi" in m.rest
    finally:
        await ctrl.mqtt.stop(); await stop(m, tasks); await b.stop()


@pytest.mark.asyncio
async def test_schalter_aus_home_assistant(tmp_path):
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b)
    try:
        await wait_for(lambda: "solasi/test" in b.retained and b.subs)
        await b.send("solasi/test/set", "ON")
        await wait_for(lambda: ctrl.cfg["dry_run"] is True and b.retained.get("solasi/test") == "ON")
        await b.send("solasi/control/set", "OFF")
        await wait_for(lambda: ctrl.cfg["enabled"] is False and b.retained.get("solasi/control") == "OFF")
        await b.send("solasi/stop/set", "ON")
        await wait_for(lambda: ctrl.stopped and b.retained.get("solasi/stop") == "ON")
        await b.send("solasi/stop/set", "OFF")
        await wait_for(lambda: not ctrl.stopped and b.retained.get("solasi/stop") == "OFF")
        await b.send("solasi/unbekannt/set", "ON")      # wird ignoriert
        await asyncio.sleep(0.2)
    finally:
        await ctrl.mqtt.stop(); await stop(m, tasks); await b.stop()


@pytest.mark.asyncio
async def test_abbruch_und_neuaufbau_mit_discovery(tmp_path):
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b)
    try:
        await wait_for(lambda: "solasi/pv_w" in b.retained)
        n = len(b.connects)
        b.retained.clear()
        b.drop()
        await wait_for(lambda: len(b.connects) > n and "solasi/pv_w" in b.retained and "homeassistant/sensor/solasi/pv_w/config" in b.retained, timeout=8)
    finally:
        await ctrl.mqtt.stop(); await stop(m, tasks); await b.stop()


@pytest.mark.asyncio
async def test_ohne_broker_bleiben_virtuelle_entitaeten(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        cfg = json.loads(json.dumps(ctrl.cfg)); cfg["mqtt"].update(host="127.0.0.1", port=1)   # nichts erreichbar
        ctrl.store.save(cfg); ctrl.mqtt.retry_s = 0.2; ctrl.mqtt.start()
        await wait_for(lambda: "sensor.solasi_pv_power" in m.rest or "sensor.solasi_house_power" in m.rest or "sensor.solasi_target_power" in m.rest)
        assert ctrl.mqtt.status["state"] == "fehler"
        assert any("MQTT nicht verfügbar" in e["msg"] for e in ctrl.events)
    finally:
        await ctrl.mqtt.stop(); await stop(m, tasks)


@pytest.mark.asyncio
async def test_ausgeschaltet_verbindet_nicht(tmp_path):
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b, enabled=False)
    try:
        await asyncio.sleep(0.6)
        assert not b.connects and ctrl.mqtt.status["state"] == "aus"
    finally:
        await ctrl.mqtt.stop(); await stop(m, tasks); await b.stop()


@pytest.mark.asyncio
async def test_geordnetes_beenden_meldet_offline(tmp_path):
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b)
    try:
        await wait_for(lambda: b.retained.get("solasi/availability") == "online")
        await ctrl.mqtt.stop()
        assert b.retained["solasi/availability"] == "offline"
    finally:
        await stop(m, tasks); await b.stop()


@pytest.mark.asyncio
async def test_selbsttest_zeigt_mqtt(tmp_path):
    import selfcheck
    b = FakeBroker("u", "p"); await b.start()
    m, ctrl, ha, tasks = await with_bridge(str(tmp_path), b)
    try:
        await wait_for(lambda: ctrl.mqtt.status["state"] == "verbunden")
        items = [i for i in selfcheck.run(ctrl.cfg, ha, ctrl)["items"] if i["item"] == "MQTT-Entitäten"]
        assert items and items[0]["status"] == "ok"
        await ctrl.mqtt.stop()
        items = [i for i in selfcheck.run(ctrl.cfg, ha, ctrl)["items"] if i["item"] == "MQTT-Entitäten"]
        assert items[0]["status"] == "info"       # nach dem Beenden: aus
    finally:
        await stop(m, tasks); await b.stop()
