import asyncio, copy, json, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
import watchdog
from controller import DEFAULT_CONFIG
from test_integration import start, stop, wait_for
from test_decide import mk_cfg


def cfg_with(**units):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["units"][0].update(name="Anker", num="number.p", dir="select.d", mode="select.m", fallback_mode="self_consumption")
    cfg["units"][1].update(units.get("b", {}))
    return cfg


# ---------------- Aufbau der Automation ----------------
def test_aufbau_anker_mit_meldung():
    cfg = cfg_with(); cfg["notify"]["service"] = "notify.mobile_app_pixel"; cfg["safety"]["watchdog_min"] = 4
    auto, note = watchdog.build(cfg)
    assert auto["id"] == "solasi_waechter" and auto["alias"] == "SOLASI Wächter" and note == "ok"
    assert [t["platform"] for t in auto["trigger"]] == ["template", "homeassistant"]
    assert "sensor.solasi_heartbeat" in auto["trigger"][0]["value_template"] and "> 240" in auto["trigger"][0]["value_template"]
    acts = auto["action"][2:]
    assert acts[0]["then"][0]["data"] == {"option": "self_consumption"} and acts[0]["then"][0]["target"] == {"entity_id": "select.m"}
    assert "not is_state('select.m', 'self_consumption')" in acts[0]["if"][0]["value_template"]
    assert acts[-1]["service"] == "notify.mobile_app_pixel" and acts[-1]["continue_on_error"] is True

def test_aufbau_persistent_notification_und_fernsteuerung():
    cfg = cfg_with(b=dict(driver="modal", name="Venus", dir="select.f", num="number.d", num_chg="number.c", enable="switch.rs485",
                          mode="select.u", fallback_mode="anti_feed"))
    cfg["notify"]["service"] = "persistent_notification"
    auto, _ = watchdog.build(cfg)
    flat = json.dumps(auto)
    assert "select.f" in flat and '"stop"' in flat                         # Moduswähler auf Stop
    assert "anti_feed" in flat and "switch.rs485" in flat
    assert auto["action"][-1]["service"] == "persistent_notification.create"
    off = [a for a in auto["action"] if a.get("service") == "homeassistant.turn_off"][0]
    assert off["target"]["entity_id"] == ["switch.rs485"]

def test_aufbau_limit_und_script():
    cfg = copy.deepcopy(DEFAULT_CONFIG); cfg["units"][0].update(driver="limit", name="WR", num="number.l", fallback_value="800")
    cfg["units"][1].update(driver="script", name="Victron", script="script.v")
    auto, _ = watchdog.build(cfg)
    svc = [a["service"] for a in auto["action"][2:]]
    assert svc == ["number.set_value", "script.turn_on"]
    assert auto["action"][3]["data"]["variables"]["mode"] == "release"

def test_nichts_zu_tun_oder_ausgeschaltet():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    assert watchdog.build(cfg)[0] is None
    cfg = cfg_with(); cfg["safety"]["watchdog"] = False
    assert watchdog.build(cfg) == (None, "ausgeschaltet")
    cfg = cfg_with(); cfg["units"][0]["fallback_mode"] = ""; assert watchdog.build(cfg)[0] is None      # kein Rückfall -> nichts zu tun

def test_pruefsumme_aendert_sich_mit_der_konfiguration():
    a = watchdog.digest(watchdog.build(cfg_with())[0])
    c = cfg_with(); c["units"][0]["fallback_mode"] = "smart"
    assert a != watchdog.digest(watchdog.build(c)[0]) and a == watchdog.digest(watchdog.build(cfg_with())[0])

def test_stale_template_ignoriert_stopped_und_fehlende_entitaet():
    import jinja2
    from datetime import datetime, timedelta, timezone
    tpl = watchdog.build(cfg_with())[0]["trigger"][0]["value_template"]
    class S:
        def __init__(s, state, age): s.state = state; s.last_updated = datetime.now(timezone.utc) - timedelta(seconds=age)
    env = jinja2.Environment(); env.globals["now"] = lambda: datetime.now(timezone.utc)
    def run(states):
        env.globals["states"] = type("X", (), {"__getitem__": lambda self, k: states.get(k)})()
        return env.from_string(tpl).render().strip()
    hb = "sensor.solasi_heartbeat"
    assert run({hb: S("2026-10-04T12:00:00", 30)}) == "False"
    assert run({hb: S("2026-10-04T12:00:00", 400)}) == "True"
    assert run({hb: S("stopped", 4000)}) == "False"                         # geordnet beendet: kein Alarm
    assert run({hb: S("unavailable", 4000)}) == "False" and run({}) == "False"


# ---------------- Abgleich mit Home Assistant ----------------
async def wd_setup(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    ctrl.cfg["units"][0]["fallback_mode"] = "self_consumption"
    ctrl._wd_path = os.path.join(str(tmp_path), "wd.json"); ctrl._wd_hash = ""
    return m, ctrl, ha, tasks


@pytest.mark.asyncio
async def test_automation_wird_angelegt_und_nicht_doppelt(tmp_path):
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        await ctrl.sync_watchdog()
        assert ctrl.watchdog["state"] == "aktiv" and m.automation_posts == ["solasi_waechter"]
        body = m.automations["solasi_waechter"]
        assert body["alias"] == "SOLASI Wächter" and any("select.mode_a" in json.dumps(a) for a in body["action"])
        assert ctrl.watchdog["json"] and json.loads(ctrl.watchdog["json"])["id"] == "solasi_waechter"
        assert await wait_for(lambda: "automation.solasi_waechter" in ha.states)
        await ctrl.sync_watchdog(); await ctrl.sync_watchdog()
        assert m.automation_posts == ["solasi_waechter"]                    # unverändert: kein erneutes Schreiben
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_automation_wird_bei_aenderung_aktualisiert_und_bei_abschalten_entfernt(tmp_path):
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        await ctrl.sync_watchdog()
        ctrl.cfg["units"][0]["fallback_mode"] = "smart"
        await ctrl.sync_watchdog()
        assert len(m.automation_posts) == 2 and ctrl.watchdog["detail"] == "aktualisiert"
        assert "smart" in json.dumps(m.automations["solasi_waechter"])
        ctrl.cfg["safety"]["watchdog"] = False
        await ctrl.sync_watchdog()
        assert "solasi_waechter" not in m.automations and ctrl.watchdog["state"] == "aus"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_fehlende_rechte_fuehren_zu_manuell_mit_text(tmp_path):
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        m.config_status = 403
        await ctrl.sync_watchdog()
        assert ctrl.watchdog["state"] == "manuell" and "403" in ctrl.watchdog["detail"]
        assert json.loads(ctrl.watchdog["json"])["alias"] == "SOLASI Wächter"          # Text zum Einfügen liegt vor
        assert m.automations == {}
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_abgleich_beim_verbinden_und_nach_dem_speichern(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer
    import main as appmain
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        assert await wait_for(lambda: ctrl.watchdog["state"] == "aktiv", 8)           # post_connect hat abgeglichen
        n = len(m.automation_posts)
        async with TestClient(TestServer(appmain.build_app(ctrl, ctrl.store, ha))) as c:
            assert (await (await c.get("/api/watchdog")).json())["state"] == "aktiv"
            cfg = json.loads(json.dumps(ctrl.cfg)); cfg["units"][0]["fallback_mode"] = "smart"
            assert (await (await c.post("/api/config", json=cfg)).json())["ok"]
            assert await wait_for(lambda: len(m.automation_posts) == n + 1, 8)
            r = await (await c.post("/api/watchdog/sync")).json(); assert r["state"] == "aktiv"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_geordnetes_beenden_meldet_stopped_hartes_nicht(tmp_path):
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        ctrl.heartbeat_interval = 0.2
        await wait_for(lambda: "sensor.solasi_heartbeat" in m.rest)
        await ctrl.shutdown()
        assert m.rest["sensor.solasi_heartbeat"]["state"] == "stopped"
        await asyncio.sleep(0.8)
        assert m.rest["sensor.solasi_heartbeat"]["state"] == "stopped"                # Lebenszeichen läuft nicht weiter
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_ohne_freigabe_beim_beenden_bleibt_der_waechter_aktiv(tmp_path):
    m, ctrl, ha, tasks = await wd_setup(tmp_path)
    try:
        ctrl.cfg["safety"]["release_on_stop"] = False
        ctrl.heartbeat_interval = 0.2
        await wait_for(lambda: "sensor.solasi_heartbeat" in m.rest)
        await ctrl.shutdown()
        assert m.rest["sensor.solasi_heartbeat"]["state"] != "stopped"               # Wächter soll später eingreifen
    finally:
        await stop(m, tasks)
