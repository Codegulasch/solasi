import asyncio, copy, os, sys, tempfile
from datetime import datetime, timezone
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
import drivers
from controller import DEFAULT_CONFIG, Controller, ConfigStore, decide
from ha import HA
from mock_ha import MockHA
from test_decide import mk_cfg, mk_unit, mk_snap
from test_integration import wait_for, stop

NAMES = DEFAULT_CONFIG["names"]


class FakeHA:
    def __init__(self, states=None, attrs=None):
        self.s = states or {}; self.a = attrs or {}
    def state(self, e): return self.s.get(e)
    def attr(self, e, n, d=None): return (self.a.get(e) or {}).get(n, d)


def unit(**kw):
    u = copy.deepcopy(DEFAULT_CONFIG["units"][0]); u.update(kw); return u


# ---------------- Anker (Betrag + Richtung) ----------------
def test_anker_lesen_und_befehle():
    u = unit(num="number.p", dir="select.d")
    ha = FakeHA({"number.p": "300", "select.d": "charge"})
    s = drivers.read(ha, u, NAMES)
    assert s["has"] and s["set"] == -300 and s["dir"] == "charge"
    cmds = drivers.commands(u, s, 200, False, NAMES, ha)
    assert [c[1] for c in cmds] == ["set_value", "select_option", "set_value"]          # erst 0, dann Richtung, dann Leistung
    assert cmds[0][2]["value"] == 0 and cmds[1][2]["option"] == "discharge" and cmds[2][2]["value"] == 200

def test_anker_abregelung_erzwingt_entladen_mit_null():
    u = unit(num="number.p", dir="select.d"); ha = FakeHA({"number.p": "0", "select.d": "charge"})
    s = drivers.read(ha, u, NAMES)
    assert drivers.needs_write(u, s, 0, True, 10, False, NAMES)
    cmds = drivers.commands(u, s, 0, True, NAMES, ha)
    assert cmds[-1][2]["value"] == 0 and any(c[2].get("option") == "discharge" for c in cmds)


# ---------------- signed (eine Zahl mit Vorzeichen) ----------------
def test_signed_vorzeichen_und_begrenzung():
    u = unit(driver="signed", num="number.passive", sign="discharge_positive")
    ha = FakeHA({"number.passive": "-500"}, {"number.passive": {"min": -3000, "max": 3000}})
    s = drivers.read(ha, u, NAMES)
    assert s["set"] == -500
    assert drivers.commands(u, s, 400, False, NAMES, ha)[0][2]["value"] == 400
    assert drivers.commands(u, s, 5000, False, NAMES, ha)[0][2]["value"] == 3000                 # Begrenzung auf max
    assert drivers.commands(u, s, -250, False, NAMES, ha)[0][2]["value"] == -250
    inv = unit(driver="signed", num="number.passive", sign="charge_positive")
    assert drivers.read(ha, inv, NAMES)["set"] == 500                                            # Vorzeichen umgekehrt
    assert drivers.commands(inv, s, 400, False, NAMES, ha)[0][2]["value"] == -400

def test_signed_nutzt_modus_wachter():
    u = unit(driver="signed", num="number.p", mode="select.m", mode_option="Passive")
    ha = FakeHA({"number.p": "0", "select.m": "Auto"})
    g = drivers.guard_commands(u, NAMES, ha)
    assert len(g) == 1 and g[0][2] == {"entity_id": "select.m", "option": "Passive"}
    ha.s["select.m"] = "Passive"
    assert drivers.guard_commands(u, NAMES, ha) == []


# ---------------- limit (nur Entladen) ----------------
def test_limit_kann_nicht_laden_und_sendet_nie_negativ():
    u = unit(driver="limit", num="number.limit")
    assert drivers.can_charge(u) is False and not drivers.curtail_enabled(u)
    ha = FakeHA({"number.limit": "250"}); s = drivers.read(ha, u, NAMES)
    assert s["set"] == 250
    assert drivers.commands(u, s, -300, False, NAMES, ha)[0][2]["value"] == 0

def test_limit_wird_in_der_regelung_nie_zum_laden_geplant():
    cfg = mk_cfg(); cfg["units"][0].update(driver="limit", num="number.l"); cfg["units"][1].update(driver="limit", num="number.l2")
    units = [mk_unit(cfg, 0, 50), mk_unit(cfg, 1, 50)]
    d = decide(cfg, mk_snap(cfg, -800, units))
    assert not d["want_chg"] and all(u["p"] >= 0 for u in units)

def test_gemischte_flotte_anker_und_limit():
    cfg = mk_cfg(); cfg["units"][1].update(driver="limit", num="number.l2")
    units = [mk_unit(cfg, 0, 50), mk_unit(cfg, 1, 50)]
    d = decide(cfg, mk_snap(cfg, -600, units))
    assert d["want_chg"] and units[0]["p"] < 0 and units[1]["p"] == 0         # nur der Anker lädt


# ---------------- modal (Modus + Leistungen) ----------------
MODAL = dict(driver="modal", dir="select.force", num="number.dis", num_chg="number.chg")

def test_modal_lesen():
    u = unit(**MODAL)
    for mode, dis, chg, expect in (("discharge", "300", "0", 300), ("charge", "0", "700", -700), ("stop", "100", "100", 0)):
        ha = FakeHA({"select.force": mode, "number.dis": dis, "number.chg": chg})
        assert drivers.read(ha, u, NAMES)["set"] == expect
    assert drivers.read(FakeHA({"select.force": "unavailable", "number.dis": "0", "number.chg": "0"}), u, NAMES)["has"] is False

def test_modal_befehle_reihenfolge_und_modus():
    u = unit(**MODAL); ha = FakeHA({"select.force": "stop", "number.dis": "0", "number.chg": "0"})
    s = drivers.read(ha, u, NAMES)
    c = drivers.commands(u, s, 400, False, NAMES, ha)
    assert [(x[2]["entity_id"], x[2].get("value", x[2].get("option"))) for x in c] == [("number.chg", 0), ("number.dis", 400), ("select.force", "discharge")]
    c = drivers.commands(u, s, -600, False, NAMES, ha)
    assert [(x[2]["entity_id"], x[2].get("value", x[2].get("option"))) for x in c] == [("number.chg", 600), ("number.dis", 0), ("select.force", "charge")]
    c = drivers.commands(u, s, 0, False, NAMES, ha)
    assert c[-1][2] == {"entity_id": "select.force", "option": "stop"} or s["dir"] == "stop" and len(c) == 2        # Stop, wenn schon Stop: kein Moduswechsel nötig

def test_modal_ohne_ladezahl_laedt_nie():
    u = unit(driver="modal", dir="select.force", num="number.dis")
    assert drivers.can_charge(u) is False

def test_modal_eigene_optionsnamen_und_fernsteuerung():
    u = unit(**MODAL, dir_dis="Entladen", dir_chg="Laden", dir_stop="Standby", enable="switch.rs485", mode="select.user", mode_option="Manuell")
    ha = FakeHA({"select.force": "Standby", "number.dis": "0", "number.chg": "0", "switch.rs485": "off", "select.user": "Auto"})
    g = drivers.guard_commands(u, NAMES, ha)
    assert [x[2]["entity_id"] for x in g] == ["switch.rs485", "select.user"]       # erst Fernsteuerung, dann Arbeitsmodus
    c = drivers.commands(u, drivers.read(ha, u, NAMES), 200, False, NAMES, ha)
    assert c[-1][2]["option"] == "Entladen"

def test_modal_abregelung_entladen_mit_null():
    u = unit(**MODAL); ha = FakeHA({"select.force": "stop", "number.dis": "0", "number.chg": "0"})
    s = drivers.read(ha, u, NAMES)
    assert drivers.needs_write(u, s, 0, True, 10, False, NAMES)
    c = drivers.commands(u, s, 0, True, NAMES, ha)
    assert c[-1][2]["option"] == "discharge" and c[-2][2]["value"] == 0


# ---------------- script ----------------
def test_script_treiber():
    u = unit(driver="script", script="script.victron_setpoint", name="Victron")
    assert drivers.configured(u) and not drivers.configured(unit(driver="script"))
    s = drivers.read(FakeHA(), u, NAMES, {"Victron": 150.0})
    assert s["set"] == 150.0 and s["has"]
    c = drivers.commands(u, s, -250, False, NAMES, FakeHA())[0]
    assert c[:2] == ("script", "turn_on") and c[2]["variables"] == {"power_w": -250, "mode": "charge", "unit": "Victron"}
    assert drivers.commands(u, s, 0, False, NAMES, FakeHA())[0][2]["variables"]["mode"] == "idle"
    assert not drivers.curtail_enabled(u)


# ---------------- Integration gegen den simulierten HA ----------------
async def boot(tmp_path, unit_cfgs, states):
    m = MockHA(); url = await m.start()
    m.set_state("sensor.grid", 400, broadcast=False)
    for k, v in states.items():
        m.set_state(k, v[0] if isinstance(v, tuple) else v, v[1] if isinstance(v, tuple) else None, broadcast=False)
    store = ConfigStore(os.path.join(str(tmp_path), "s.json")); cfg = store.cfg
    cfg["enabled"] = True; cfg["dry_run"] = False; cfg["grid"]["entity"] = "sensor.grid"
    for i, uc in enumerate(unit_cfgs):
        cfg["units"][i].update(uc)
    cfg["units"][len(unit_cfgs):] = []
    cfg["control"].update(min_gap=0, heartbeat=0.3, total_max_dis=2000)
    store.save(cfg)
    ctrl = Controller(None, store)
    ha = HA(url, "TOKEN", on_entity_event=ctrl.on_entity_event, api_url=m.api_url, on_connected=ctrl.post_connect); ctrl.ha = ha
    tasks = [asyncio.create_task(ha.run()), asyncio.create_task(ctrl.run())]
    m._ha = ha
    return m, ctrl, tasks


@pytest.mark.asyncio
async def test_integration_modal_marstek_stil(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [dict(driver="modal", name="Venus", dir="select.force", num="number.dis", num_chg="number.chg",
                                               soc="sensor.soc", enable="switch.rs485", mode="select.user", mode_option="manual",
                                               real_dis="sensor.rd", real_chg="sensor.rc")],
        {"select.force": "stop", "number.dis": ("0", {"min": 0, "max": 2500}), "number.chg": ("0", {"min": 0, "max": 2500}),
         "sensor.soc": 70, "switch.rs485": "off", "select.user": "anti_feed", "sensor.rd": 0, "sensor.rc": 0})
    try:
        assert await wait_for(lambda: m.states["select.force"]["state"] == "discharge" and m.states["number.dis"]["state"] == "390", 8), \
            (m.states["select.force"]["state"], m.states["number.dis"]["state"], m.calls)
        assert m.states["switch.rs485"]["state"] == "on" and m.states["select.user"]["state"] == "manual"
        order = [c[2].get("entity_id") for c in m.calls]
        assert order.index("switch.rs485") < order.index("select.user") < order.index("number.dis") < order.index("select.force")
        m.set_state("sensor.grid", -600)                          # Einspeisung: Laden
        assert await wait_for(lambda: m.states["select.force"]["state"] == "charge" and m.states["number.chg"]["state"] != "0", 8), m.calls[-6:]
        assert m.states["number.dis"]["state"] == "0"
        m.set_state("sensor.grid", 0)
        m.set_state("number.chg", 0); m.set_state("select.force", "stop")
        await asyncio.sleep(1.0)
        assert m.states["select.force"]["state"] == "stop"           # im Leerlauf bleibt alles aus
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_integration_signed_mit_modus(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [dict(driver="signed", name="Passiv", num="number.passive", soc="sensor.soc",
                                               mode="select.mode", mode_option="Passive")],
        {"number.passive": ("0", {"min": -3000, "max": 3000}), "sensor.soc": 60, "select.mode": "Auto"})
    try:
        assert await wait_for(lambda: m.states["select.mode"]["state"] == "Passive" and int(float(m.states["number.passive"]["state"])) > 0, 8), m.calls
        m.set_state("sensor.grid", -800)
        assert await wait_for(lambda: int(float(m.states["number.passive"]["state"])) < 0, 8), m.states["number.passive"]
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_integration_limit_nur_entladen(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [dict(driver="limit", name="WR", num="number.limit", soc="sensor.soc")],
                                {"number.limit": ("0", {"min": 0, "max": 800}), "sensor.soc": 60})
    try:
        assert await wait_for(lambda: float(m.states["number.limit"]["state"]) > 0, 8)
        m.set_state("sensor.grid", -900)
        await asyncio.sleep(1.5)
        assert float(m.states["number.limit"]["state"]) == 0           # nie negativ, kein Netzladen
        assert all(c[2].get("value", 0) >= 0 for c in m.calls if c[:2] == ("number", "set_value"))
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_integration_script_treiber(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [dict(driver="script", name="Victron", script="script.set_power", soc="sensor.soc")],
                                {"script.set_power": "off", "sensor.soc": 60})
    try:
        assert await wait_for(lambda: any(c[:2] == ("script", "turn_on") for c in m.calls), 8)
        call = next(c for c in m.calls if c[:2] == ("script", "turn_on"))
        assert call[2]["entity_id"] == "script.set_power" and call[2]["variables"]["mode"] == "discharge" and call[2]["variables"]["power_w"] > 0
        # ohne Rückkopplung im Simulator steigt der Sollwert bis zum Limit (800 W), danach bleibt er stehen
        assert await wait_for(lambda: ctrl._script_mem.get("Victron") == 800, 8)
        await asyncio.sleep(0.8); n = len([c for c in m.calls if c[0] == "script"])
        await asyncio.sleep(2.0)
        assert len([c for c in m.calls if c[0] == "script"]) == n        # kein Dauerfeuer bei gleichem Sollwert
        assert ctrl._script_mem["Victron"] > 0
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_integration_gemischte_flotte(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [
        dict(name="Anker", num="number.pwr_ma", dir="select.da", mode="select.ma", soc="sensor.soca"),
        dict(driver="limit", name="WR", num="number.limit", soc="sensor.socb")],
        {"number.pwr_ma": "unavailable", "select.da": "discharge", "select.ma": "self_consumption", "sensor.soca": 80,
         "number.limit": ("0", {"min": 0, "max": 800}), "sensor.socb": 60})
    try:
        # unavailable-Zahl des Anker wird durch den Modus-Wächter verfügbar; mock setzt sie bei „…_a“ auf 0
        assert await wait_for(lambda: float(m.states["number.limit"]["state"]) > 0, 8)
        assert await wait_for(lambda: m.states["select.ma"]["state"] == "third_party_control", 8)
    finally:
        await stop(m, tasks)


# ---------------- Systemprüfung und Replay für andere Speichertypen ----------------
def test_systempruefung_modal_und_script(tmp_path):
    import selfcheck
    store = ConfigStore(str(tmp_path / "c.json")); ctrl = Controller(None, store); ha = ctrl.ha = HA("ws://x", "t"); ha.connected = True
    cfg = ctrl.cfg
    ha.states = {
        "sensor.grid": {"state": "5", "attributes": {}},
        "select.force": {"state": "stop", "attributes": {"options": ["stop", "charge", "discharge"]}},
        "number.dis": {"state": "0", "attributes": {}}, "number.chg": {"state": "0", "attributes": {}},
        "switch.rs485": {"state": "off", "attributes": {}},
        "select.user": {"state": "auto", "attributes": {"options": ["auto", "manual"]}},
        "sensor.soc": {"state": "50", "attributes": {}}, "sensor.p": {"state": "-100", "attributes": {"unit_of_measurement": "W"}},
        "script.set": {"state": "off", "attributes": {}},
    }
    cfg["grid"]["entity"] = "sensor.grid"
    cfg["units"][0].update(driver="modal", name="Venus", dir="select.force", num="number.dis", num_chg="number.chg", enable="switch.rs485",
                           mode="select.user", mode_option="manual", soc="sensor.soc", power="sensor.p")
    cfg["units"][1].update(driver="script", name="Victron", script="script.set", soc="sensor.soc")
    r = selfcheck.run(cfg, ha, ctrl); by = {(i["area"], i["item"]): i for i in r["items"]}
    assert by[("Speicher Venus", "Modus-Optionen")]["status"] == "ok"
    assert by[("Speicher Venus", "Modus-Option")]["status"] == "ok"
    assert by[("Speicher Venus", "Echte Leistung (Sensor mit Vorzeichen)")]["status"] == "ok"
    assert by[("Speicher Venus", "Fernsteuerung (Schalter)")]["status"] == "ok"
    assert by[("Speicher Victron", "Skript")]["status"] == "ok" and "power_w" in by[("Speicher Victron", "Aufruf")]["text"]
    cfg["units"][0]["dir_stop"] = "standby"                           # Option gibt es nicht
    r = selfcheck.run(cfg, ha, ctrl); by = {(i["area"], i["item"]): i for i in r["items"]}
    assert by[("Speicher Venus", "Modus-Optionen")]["status"] == "error" and "standby" in by[("Speicher Venus", "Modus-Optionen")]["text"]
    cfg["units"][1]["script"] = ""
    r = selfcheck.run(cfg, ha, ctrl)
    assert any(i["area"] == "Speicher Victron" and i["item"] == "Konfiguration" and i["status"] == "error" for i in r["items"])


def test_replay_mit_signiertem_leistungssensor():
    import replay
    cfg = mk_cfg(); cfg["grid"]["entity"] = "sensor.g"
    cfg["units"][0].update(driver="signed", num="number.p", soc="sensor.s", pv="sensor.pv", power="sensor.bat", power_sign="charge_positive")
    cfg["units"][1].update(driver="signed", num="", soc="", pv="")                     # nicht eingerichtet
    assert replay.check_requirements(cfg) == []                                         # Leistungssensor ersetzt Lade-/Entladesensoren
    t0 = 1_700_000_000.0
    def ser(eid, vals): return [{"entity_id": eid, "state": str(v), "last_changed": datetime.fromtimestamp(t0 + i * 10, timezone.utc).isoformat()} for i, v in enumerate(vals)]
    raw = [ser("sensor.g", [100, 100, 100, 100]), ser("sensor.s", [50] * 4), ser("sensor.pv", [0] * 4), ser("sensor.bat", [300, -200, 0, 150])]
    data = replay.build_data(cfg, raw, t0, t0 + 40, 10)
    u = data["units"][0]
    assert u["rd"] == [0.0, 200.0, 0.0, 0.0] and u["rc"] == [300.0, 0.0, 0.0, 150.0]  # positiv = Laden -> rc, negativ = Entladen -> rd
