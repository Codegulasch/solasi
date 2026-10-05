import asyncio, copy, json, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
import drivers
from controller import DEFAULT_CONFIG, Controller, ConfigStore
from ha import HA
from mock_ha import MockHA
from test_integration import start, stop, wait_for, build_states
from test_drivers import FakeHA, unit, NAMES


# ---------------- Freigabe-Befehle je Treiber ----------------
def test_freigabe_anker_erst_null_dann_eigenverbrauch():
    u = unit(num="number.p", dir="select.d", mode="select.m", fallback_mode="self_consumption")
    ha = FakeHA({"number.p": "300", "select.d": "discharge", "select.m": "third_party_control"})
    c = drivers.release_commands(u, drivers.read(ha, u, NAMES), NAMES, ha)
    assert [(x[1], x[2].get("value", x[2].get("option"))) for x in c] == [("set_value", 0), ("select_option", "self_consumption")]

def test_freigabe_anker_nicht_verfuegbar_nur_modus():
    u = unit(num="number.p", dir="select.d", mode="select.m", fallback_mode="self_consumption")
    ha = FakeHA({"number.p": "unavailable", "select.d": "discharge", "select.m": "third_party_control"})
    c = drivers.release_commands(u, drivers.read(ha, u, NAMES), NAMES, ha)
    assert [x[2]["entity_id"] for x in c] == ["select.m"]
    ha.s["select.m"] = "self_consumption"
    assert drivers.release_commands(u, drivers.read(ha, u, NAMES), NAMES, ha) == []          # schon im Zielmodus

def test_freigabe_ohne_rueckfallmodus_setzt_nur_null():
    u = unit(num="number.p", dir="select.d", mode="select.m")
    ha = FakeHA({"number.p": "200", "select.d": "discharge", "select.m": "third_party_control"})
    c = drivers.release_commands(u, drivers.read(ha, u, NAMES), NAMES, ha)
    assert len(c) == 1 and c[0][2]["value"] == 0

def test_freigabe_modal_stop_dann_fernsteuerung_aus_dann_modus():
    u = unit(driver="modal", dir="select.f", num="number.d", num_chg="number.c", enable="switch.rs", mode="select.u", fallback_mode="anti_feed")
    ha = FakeHA({"select.f": "discharge", "number.d": "300", "number.c": "0", "switch.rs": "on", "select.u": "manual"})
    c = drivers.release_commands(u, drivers.read(ha, u, NAMES), NAMES, ha)
    assert [(x[2]["entity_id"], x[2].get("value", x[2].get("option"))) for x in c] == [
        ("number.d", 0), ("select.f", "stop"), ("switch.rs", None), ("select.u", "anti_feed")]

def test_freigabe_signed_limit_script():
    ha = FakeHA({"number.p": "250", "select.m": "Passive", "number.l": "400"})
    s = unit(driver="signed", num="number.p", mode="select.m", fallback_mode="Auto")
    c = drivers.release_commands(s, drivers.read(ha, s, NAMES), NAMES, ha)
    assert [x[2].get("value", x[2].get("option")) for x in c] == [0, "Auto"]
    l = unit(driver="limit", num="number.l", fallback_value="800")
    assert drivers.release_commands(l, drivers.read(ha, l, NAMES), NAMES, ha)[0][2]["value"] == 800
    assert drivers.release_commands(unit(driver="limit", num="number.l"), drivers.read(ha, l, NAMES), NAMES, ha) == []       # leer = unverändert
    sc = unit(driver="script", script="script.x", name="V")
    c = drivers.release_commands(sc, drivers.read(ha, sc, NAMES), NAMES, ha)[0]
    assert c[2]["variables"] == {"power_w": 0, "mode": "release", "unit": "V"}


# ---------------- Kill-Switch im laufenden Betrieb ----------------
async def live(tmp_path, **cfgmods):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    for u in ctrl.cfg["units"]:
        u["fallback_mode"] = "self_consumption"
    ctrl.cfg["notify"].update(service="persistent_notification", delay_min=0)
    for k, v in cfgmods.items():
        ctrl.cfg[k].update(v)
    ctrl.safety_path = os.path.join(str(tmp_path), "safety.json")
    return m, ctrl, ha, tasks


@pytest.mark.asyncio
async def test_kill_gibt_speicher_frei_und_stoppt_die_regelung(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.calls.clear()
        assert await ctrl.kill("Test", "manual") is True
        for k in "ab":
            assert m.states[f"select.mode_{k}"]["state"] == "self_consumption"         # Eigenverbrauch
            assert m.states[f"number.pwr_{k}"]["state"] == "0"
        calls = [(c[0], c[2].get("entity_id"), c[2].get("value", c[2].get("option"))) for c in m.calls]
        assert calls.index(("number", "number.pwr_a", 0)) < calls.index(("select", "select.mode_a", "self_consumption"))   # erst 0 W, dann Modus
        assert ctrl.stopped and ctrl.status["safety"]["state"] == "stopped"
        assert any(c[0] == "persistent_notification" and "gestoppt" in c[2]["title"] for c in m.calls)
        assert await ctrl.kill("nochmal") is False                                       # zweites Mal harmlos
        # während des Stopps wird nichts mehr geschrieben, auch bei Last
        m.calls.clear(); m.set_state("sensor.grid", 900)
        await asyncio.sleep(1.5)
        assert [c for c in m.calls if c[0] in ("number", "select")] == []
        assert await wait_for(lambda: ctrl.status.get("safety", {}).get("state") == "stopped")
        assert ctrl._entity_payloads()["sensor.solasi"][0] == "Gestoppt" and ctrl._entity_payloads()["sensor.solasi"][1]["mode"] == "stopped"
        # Fortsetzen: Regelung übernimmt wieder und schaltet den Modus zurück
        assert ctrl.resume() is True
        assert await wait_for(lambda: m.states["select.mode_a"]["state"] == "third_party_control" and float(m.states["number.pwr_a"]["state"]) > 0, 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_kill_im_testmodus_aendert_nichts_am_geraet(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        ctrl.cfg["dry_run"] = True
        m.calls.clear()
        await ctrl.kill("Test", "manual")
        assert [c for c in m.calls if c[0] in ("number", "select")] == [] and ctrl.stopped
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_freigabe_beim_stoppen_abschaltbar(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path, safety={"release_on_stop": False})
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.calls.clear(); await ctrl.kill("Test")
        assert [c for c in m.calls if c[0] in ("number", "select")] == []
        assert m.states["select.mode_a"]["state"] == "third_party_control"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_not_aus_schalter_stoppt_und_setzt_fort(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path, safety={"kill_entity": "input_boolean.notaus"})
    try:
        m.set_state("input_boolean.notaus", "off")
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.set_state("input_boolean.notaus", "on")
        assert await wait_for(lambda: ctrl.stopped and m.states["select.mode_a"]["state"] == "self_consumption", 8)
        assert ctrl.safety["source"] == "entity"
        m.set_state("input_boolean.notaus", "off")                         # Schalter aus -> automatisch weiter
        assert await wait_for(lambda: not ctrl.stopped, 8)
        assert await wait_for(lambda: m.states["select.mode_a"]["state"] == "third_party_control", 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_zaehlerausfall_stoppt_automatisch_und_setzt_optional_fort(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path, safety={"auto_meter_min": 0.03, "resume_auto": True})
    ctrl.resume_clear_s = 1.5
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.set_state("sensor.grid", "unavailable")
        assert await wait_for(lambda: ctrl.stopped, 10), ctrl.safety
        assert ctrl.safety["source"] == "auto" and "Zähler" in ctrl.safety["reason"]
        assert await wait_for(lambda: m.states["select.mode_a"]["state"] == "self_consumption", 8)
        m.set_state("sensor.grid", 100)
        assert await wait_for(lambda: not ctrl.stopped, 10), ctrl.safety          # Zähler wieder da, nach Wartezeit weiter
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_automatisch_gestoppt_bleibt_ohne_resume_auto_gestoppt(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path, safety={"auto_meter_min": 0.03, "resume_auto": False})
    ctrl.resume_clear_s = 0.5
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.set_state("sensor.grid", "unavailable"); await wait_for(lambda: ctrl.stopped, 10)
        m.set_state("sensor.grid", 100); await asyncio.sleep(3)
        assert ctrl.stopped                                                         # muss von Hand fortgesetzt werden
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_wiederholte_befehlsfehler_stoppen(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.fail = {("number", "set_value")}
        m.set_state("sensor.grid", 1200)                                            # neuer Sollwert -> Schreiben schlägt fehl
        assert await wait_for(lambda: ctrl.stopped, 12), (ctrl.safety, list(ctrl.events)[:4])
        assert "fehl" in ctrl.safety["reason"] and ctrl.safety["source"] == "auto"
        # auch wenn „0 W“ fehlschlägt, wird der Rückfall-Modus gesetzt
        assert await wait_for(lambda: m.states["select.mode_a"]["state"] == "self_consumption", 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_stopp_ueberlebt_neustart(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        await ctrl.kill("Test")
        store2 = ConfigStore(os.path.join(str(tmp_path), "s2.json"))
        c2 = Controller(None, store2); c2.safety_path = ctrl.safety_path
        from util import load_json
        saved = load_json(ctrl.safety_path, {})
        assert saved["state"] == "stopped" and saved["reason"] == "Test"
        c3 = Controller(None, store2)                       # lädt aus SOLASI_DATA; hier gleiche Datei nutzen
        c3.safety = {**c3.safety, **saved}
        assert c3.stopped
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_beenden_gibt_frei(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        await ctrl.shutdown()
        assert m.states["select.mode_a"]["state"] == "self_consumption" and m.states["number.pwr_a"]["state"] == "0"
        assert not ctrl.stopped                              # Beenden ist kein Stopp-Zustand
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_beenden_im_testmodus_oder_ausgeschaltet_laesst_geraet_in_ruhe(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        ctrl.cfg["dry_run"] = True; m.calls.clear()
        await ctrl.shutdown()
        assert [c for c in m.calls if c[0] in ("number", "select")] == []
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_lebenszeichen_wird_regelmaessig_gesendet(tmp_path):
    m, ctrl, ha, tasks = await live(tmp_path)
    ctrl.heartbeat_interval = 0.3
    try:
        await asyncio.sleep(0.6)
        seen = set()
        for _ in range(12):
            if "sensor.solasi_heartbeat" in m.rest: seen.add(m.rest["sensor.solasi_heartbeat"]["state"])
            await asyncio.sleep(0.5)
        assert len(seen) >= 2                                # Zeitstempel ändert sich, nicht dedupliziert
        assert m.rest["sensor.solasi_heartbeat"]["attributes"]["device_class"] == "timestamp"
    finally:
        await stop(m, tasks)


# ---------------- Web-API ----------------
@pytest.mark.asyncio
async def test_web_kill_resume_und_freigabe_beim_ausschalten(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer
    import main as appmain
    m, ctrl, ha, tasks = await live(tmp_path)
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        app = appmain.build_app(ctrl, ctrl.store, ha)
        async with TestClient(TestServer(app)) as c:
            st = await (await c.get("/api/status")).json(); assert st["safety"]["state"] == "active"
            j = await (await c.post("/api/kill")).json(); assert j["stopped"] and j["changed"]
            st = await (await c.get("/api/status")).json(); assert st["safety"]["state"] == "stopped" and st["safety"]["reason"]
            j = await (await c.post("/api/resume")).json(); assert not j["stopped"]
            # Optionen eines select
            m.set_state("select.mode_a", "x", {"options": ["third_party_control", "self_consumption"]})
            await asyncio.sleep(0.2)
            o = await (await c.get("/api/entity_options?entity=select.mode_a")).json()
            assert o["options"] == ["third_party_control", "self_consumption"]
            assert (await (await c.get("/api/entity_options?entity=select.nix")).json())["options"] == []
            # Live-Steuerung wird über die Oberfläche ausgeschaltet -> Speicher werden freigegeben
            await wait_for(lambda: m.states["number.pwr_a"]["state"] not in ("0", "unavailable"))
            cfg = json.loads(json.dumps(ctrl.cfg)); cfg["enabled"] = False
            m.calls.clear()
            assert (await (await c.post("/api/config", json=cfg)).json())["ok"]
            assert await wait_for(lambda: m.states["select.mode_a"]["state"] == "self_consumption", 8), m.calls
    finally:
        await stop(m, tasks)


# ---------------- Systemprüfung: Rückfall ----------------
def test_systempruefung_rueckfall(tmp_path):
    import selfcheck
    store = ConfigStore(str(tmp_path / "c.json")); ctrl = Controller(None, store); ha = ctrl.ha = HA("ws://x", "t"); ha.connected = True
    cfg = ctrl.cfg
    ha.states = {"sensor.grid": {"state": "5", "attributes": {}}, "number.p": {"state": "0", "attributes": {}},
                 "select.d": {"state": "discharge", "attributes": {"options": ["charge", "discharge"]}},
                 "select.m": {"state": "third_party_control", "attributes": {"options": ["third_party_control", "self_consumption"]}},
                 "sensor.soc": {"state": "50", "attributes": {}}, "input_boolean.notaus": {"state": "off", "attributes": {}}}
    cfg["grid"]["entity"] = "sensor.grid"
    cfg["safety"]["kill_entity"] = "input_boolean.notaus"
    u = cfg["units"][0]; u.update(num="number.p", dir="select.d", mode="select.m", soc="sensor.soc")
    by = lambda: {(i["area"], i["item"]): i for i in selfcheck.run(cfg, ha, ctrl)["items"]}
    assert by()[("Speicher A", "Rückfall-Modus")]["status"] == "warn"            # nicht gewählt
    u["fallback_mode"] = "self_consumption"
    assert by()[("Speicher A", "Rückfall-Modus")]["status"] == "ok"
    u["fallback_mode"] = "Eigenverbrauch"                                               # Option existiert nicht
    r = by()[("Speicher A", "Rückfall-Modus")]
    assert r["status"] == "error" and "third_party_control" in r["text"]
    assert by()[("Sicherheit", "Not-Aus-Schalter")]["status"] == "ok"
    u["mode"] = ""
    assert by()[("Speicher A", "Rückfall-Modus")]["status"] == "warn"            # ohne Betriebsmodus kein Rückfall möglich
