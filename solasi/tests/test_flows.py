"""Leistungsflüsse (Solar, Batterie, Abgabe ins Haus), PV-Durchleitung und die Fälle aus der Praxis."""
import asyncio, copy, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
import drivers, replay, selfcheck
from controller import DEFAULT_CONFIG, decide
from ha import HA
from test_decide import mk_cfg, mk_unit, mk_snap
from test_drivers import FakeHA, unit, boot, NAMES
from test_integration import stop, wait_for
from datetime import datetime, timezone


# ---------------- Flüsse ----------------
def test_batterieseitig_screenshot_fall():
    """Anker-App: Solar 540 W, Batterie lädt 140 W, Netz 0 -> 400 W gehen ins Haus."""
    u = unit(real_dis="sensor.d", real_chg="sensor.c", pv="sensor.pv")
    ha = FakeHA({"sensor.d": "0", "sensor.c": "140", "sensor.pv": "540"})
    f = drivers.flows(ha, u)
    assert drivers.basis(u) == "battery"                      # Anker mit PV-Sensor: automatisch Batterieseite
    assert (f["pv"], f["bat"], f["ac"]) == (540.0, -140.0, 400.0)

def test_batterieseitig_entladen_und_netzladen():
    u = unit(real_dis="sensor.d", real_chg="sensor.c", pv="sensor.pv")
    ha = FakeHA({"sensor.d": "300", "sensor.c": "0", "sensor.pv": "200"})
    assert drivers.flows(ha, u)["ac"] == 500.0                 # PV 200 + Batterie 300
    ha = FakeHA({"sensor.d": "0", "sensor.c": "600", "sensor.pv": "0"})
    f = drivers.flows(ha, u); assert f["ac"] == -600.0 and f["bat"] == -600.0     # nachts aus dem Netz laden

def test_acseitig_ohne_und_mit_pv():
    u = unit(real_dis="sensor.d", real_chg="sensor.c", power_basis="ac")
    ha = FakeHA({"sensor.d": "400", "sensor.c": "0"})
    f = drivers.flows(ha, u); assert (f["ac"], f["bat"], f["pv"]) == (400.0, 400.0, None)
    u["pv"] = "sensor.pv"; ha.s["sensor.pv"] = "540"
    f = drivers.flows(ha, u); assert (f["ac"], f["bat"]) == (400.0, -140.0)       # Batterie = AC - PV

def test_unbekannt_ist_nicht_null():
    u = unit(real_dis="sensor.d", real_chg="sensor.c", pv="sensor.pv")
    # PV unbekannt: Die Batterie ist trotzdem bekannt, die Abgabe ins Haus aber nicht (sie braucht die PV)
    for states in ({"sensor.d": "0", "sensor.c": "140", "sensor.pv": "unavailable"},
                   {"sensor.d": "0", "sensor.c": "140"}):                           # PV-Entität gibt es nicht
        f = drivers.flows(FakeHA(states), u)
        assert f["pv"] is None and f["ac"] is None and f["bat"] == -140.0
    # Leistungssensor unbekannt: alles unbekannt
    f = drivers.flows(FakeHA({"sensor.d": "0", "sensor.c": "unknown", "sensor.pv": "540"}), u)
    assert f["ac"] is None and f["bat"] is None and f["pv"] == 540.0
    assert drivers.flows(FakeHA({"sensor.pv": "unavailable"}), unit(pv="sensor.pv"))["pv"] is None

def test_messart_automatik_und_ueberschreiben():
    assert drivers.basis(unit(pv="sensor.pv")) == "battery"
    assert drivers.basis(unit()) == "ac"                                            # ohne PV-Sensor nicht umrechenbar
    assert drivers.basis(unit(driver="signed", pv="sensor.pv")) == "ac"             # nur beim Anker-Typ automatisch
    assert drivers.basis(unit(pv="sensor.pv", power_basis="ac")) == "ac"
    assert drivers.basis(unit(driver="signed", power_basis="battery")) == "battery"

def test_signierter_sensor_mit_messart():
    ha = FakeHA({"sensor.p": "-420", "sensor.pv": "100"})
    u = unit(driver="signed", power="sensor.p", power_sign="discharge_positive", pv="sensor.pv", power_basis="battery")
    f = drivers.flows(ha, u); assert (f["bat"], f["ac"]) == (-420.0, -320.0)
    u["power_sign"] = "charge_positive"
    assert drivers.flows(ha, u)["bat"] == 420.0


# ---------------- Regelung: PV direkt ins Haus ----------------
def one_unit_snap(soc, pv, grid, setv=0.0, cfg=None):
    cfg = cfg or mk_cfg()
    u = mk_unit(cfg, 0, soc, setv); u["pv"] = pv
    return cfg, u, mk_snap(cfg, grid, [u])

def test_pv_durchleitung_bei_leerem_speicher():
    """Speicher bei 7 % (unter dem Minimum 15 %), Module liefern 540 W, Haus zieht 400 W aus dem Netz."""
    cfg, u, snap = one_unit_snap(7, 540.0, 400)
    d = decide(cfg, snap)
    assert d["want_dis"] and u["p"] == 390 and not u["elig_dis"]          # 400 - 10 W Offset, aus der PV
    assert u["pvcap"] == 530.0

def test_durchleitung_ist_durch_die_pv_begrenzt():
    cfg, u, snap = one_unit_snap(7, 200.0, 1500)
    decide(cfg, snap)
    assert u["p"] == 190                                                    # nie mehr als die Module liefern (minus 10 W)

def test_ohne_pv_oder_mit_pv_null_keine_abgabe_bei_leerem_speicher():
    for pv in (None, 0.0, 8.0):
        cfg, u, snap = one_unit_snap(7, pv, 400)
        d = decide(cfg, snap)
        assert u["p"] == 0 and not d["want_dis"], pv

def test_durchleitung_abschaltbar():
    cfg = mk_cfg(); cfg["features"]["pv_passthrough"] = False
    cfg, u, snap = one_unit_snap(7, 540.0, 400, cfg=cfg)
    decide(cfg, snap); assert u["p"] == 0

def test_eco_begrenzt_nur_den_batterieanteil():
    cfg = mk_cfg(); cfg["control"]["total_max_dis"] = 2000
    units = [mk_unit(cfg, 0, 30), mk_unit(cfg, 1, 30)]
    units[0]["pv"] = 200.0; units[1]["pv"] = 200.0
    d = decide(cfg, mk_snap(cfg, 800, units))
    assert d["eco_active"] and d["t_target"] == 530                         # 150 W Eco + 380 W PV
    assert sum(u["p"] for u in units) in (530, 540, 520)
    # ohne PV bleibt es bei der Eco-Grenze
    units = [mk_unit(cfg, 0, 30), mk_unit(cfg, 1, 30)]
    assert decide(cfg, mk_snap(cfg, 800, units))["t_target"] == 150

def test_normaler_speicher_mit_pv_unveraendert():
    cfg = mk_cfg(); cfg["control"]["total_max_dis"] = 2000
    units = [mk_unit(cfg, 0, 80), mk_unit(cfg, 1, 40)]
    for u in units: u["pv"] = 300.0
    d = decide(cfg, mk_snap(cfg, 400, units))
    assert d["t_target"] == 390 and [u["p"] for u in units] == [280, 110]    # wie ohne PV-Daten


# ---------------- Aus Home Assistant gelesen (Screenshot-Fall) ----------------
SCREENSHOT = {"number.p": "unavailable", "select.d": "discharge", "select.m": "self_consumption",
              "sensor.soc": 7, "sensor.pv": 540, "sensor.bd": 0, "sensor.bc": 140}
ANKER = dict(name="Speicher", num="number.p", dir="select.d", mode="select.m", soc="sensor.soc",
             pv="sensor.pv", real_dis="sensor.bd", real_chg="sensor.bc")


@pytest.mark.asyncio
async def test_status_zeigt_solar_haus_und_batterie_richtig(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], SCREENSHOT)
    m.set_state("sensor.grid", 0)
    ctrl.cfg["enabled"] = False                                              # nur beobachten, wie in der App-Gegenüberstellung
    try:
        assert await wait_for(lambda: ctrl.status.get("house_w") is not None, 8), ctrl.status
        st = ctrl.status
        assert st["pv_w"] == 540 and st["bat_w"] == -140 and st["house_w"] == 400 and st["grid_w"] == 0
        assert st["units"][0]["pv"] == 540
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_pv_sensor_nicht_verfuegbar_wird_unbekannt_statt_null(tmp_path):
    states = dict(SCREENSHOT); states["sensor.pv"] = "unavailable"
    m, ctrl, tasks = await boot(tmp_path, [ANKER], states)
    ctrl.cfg["enabled"] = False
    try:
        assert await wait_for(lambda: "pv_w" in ctrl.status, 8)
        st = ctrl.status
        assert st["pv_w"] is None and st["house_w"] is None        # unbekannt, nicht 0
        assert st["bat_w"] == -140                                  # die Batterieleistung ist trotzdem bekannt
        assert ctrl._entity_payloads()["sensor.solasi"][1]["pv_w"] is None
        assert "sensor.solasi_pv_power" not in ctrl._entity_payloads()
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_live_bei_sieben_prozent_gibt_pv_ans_haus(tmp_path):
    """Der gemeldete Fall: Speicher bei 7 %, 540 W Solar, Haus zieht aus dem Netz. Die PV muss ins Haus gehen."""
    states = {**SCREENSHOT, "number.pwr_ma": "unavailable", "select.mode_ma": "self_consumption"}
    m, ctrl, tasks = await boot(tmp_path, [{**ANKER, "num": "number.pwr_ma", "mode": "select.mode_ma",
                                           "mode_option": "third_party_control", "fallback_mode": "self_consumption"}], states)
    m.set_state("sensor.grid", 400, broadcast=False)
    try:
        assert await wait_for(lambda: m.states["select.mode_ma"]["state"] == "third_party_control", 8), m.calls
        assert await wait_for(lambda: m.states["number.pwr_ma"]["state"] not in ("unavailable", "0"), 8), m.calls
        v = float(m.states["number.pwr_ma"]["state"])
        assert 0 < v <= 530                                                   # nie mehr, als die Module gerade liefern
        assert m.states["select.d"]["state"] == "discharge"
    finally:
        await stop(m, tasks)


# ---------------- Selbsttest ----------------
def mk_check_ctrl(tmp_path, states, **unit_kw):
    from controller import ConfigStore, Controller
    store = ConfigStore(str(tmp_path / "c.json")); ctrl = Controller(None, store); ha = ctrl.ha = HA("ws://x", "t"); ha.connected = True
    ha.states = {k: {"state": str(v), "attributes": {}} for k, v in states.items()}
    cfg = ctrl.cfg; cfg["grid"]["entity"] = "sensor.grid"
    cfg["units"][0].update(ANKER); cfg["units"][0].update(unit_kw)
    return ctrl

def by(ctrl):
    return {(i["area"], i["item"]): i for i in selfcheck.run(ctrl.cfg, ctrl.ha, ctrl)["items"]}

def test_selbsttest_energiebilanz_und_messart(tmp_path):
    ctrl = mk_check_ctrl(tmp_path, {**SCREENSHOT, "sensor.grid": 4})
    r = by(ctrl)
    bal = r[("Energiebilanz", "Berechnet")]
    assert "Solar 540 W" in bal["text"] and "Batterie -140 W" in bal["text"] and "Haus 404 W" in bal["text"]
    assert "(automatisch)" in r[("Speicher", "Messart der Leistungssensoren")]["text"] and "Batterie" in r[("Speicher", "Messart der Leistungssensoren")]["text"]

def test_selbsttest_warnt_bei_falscher_messart(tmp_path):
    ctrl = mk_check_ctrl(tmp_path, {**SCREENSHOT, "sensor.grid": 4}, power_basis="ac")
    w = by(ctrl)[("Speicher", "Plausibilität")]
    assert w["status"] == "warn" and "Batterie" in w["hint"] and "140" in w["text"]

def test_selbsttest_batterie_ohne_pv_ist_fehler(tmp_path):
    ctrl = mk_check_ctrl(tmp_path, {**SCREENSHOT, "sensor.grid": 4}, pv="", power_basis="battery")
    assert by(ctrl)[("Speicher", "Messart Batterie")]["status"] == "error"

def test_selbsttest_pv_nicht_verfuegbar(tmp_path):
    ctrl = mk_check_ctrl(tmp_path, {**SCREENSHOT, "sensor.grid": 4, "sensor.pv": "unavailable"})
    r = by(ctrl)
    assert r[("Speicher", "PV-Leistung")]["status"] == "warn"
    assert r[("Energiebilanz", "Berechnet")]["status"] == "warn"

def test_selbsttest_vergleicht_mit_hausverbrauchssensor(tmp_path):
    ctrl = mk_check_ctrl(tmp_path, {**SCREENSHOT, "sensor.grid": 4, "sensor.haus": 900})
    ctrl.cfg["surplus"]["house"] = "sensor.haus"
    assert by(ctrl)[("Energiebilanz", "Hausverbrauch-Sensor")]["status"] == "warn"


# ---------------- Replay mit Messart ----------------
def test_replay_rechnet_batterieseitige_sensoren_um():
    cfg = mk_cfg(); cfg["grid"]["entity"] = "sensor.g"
    cfg["units"][0].update(num="number.p", dir="select.d", soc="sensor.s", pv="sensor.pv", real_dis="sensor.rd", real_chg="sensor.rc")
    cfg["units"][1].update(num="", dir="")
    t0 = 1_700_000_000.0
    def ser(eid, vals): return [{"entity_id": eid, "state": str(v), "last_changed": datetime.fromtimestamp(t0 + i * 10, timezone.utc).isoformat()} for i, v in enumerate(vals)]
    raw = [ser("sensor.g", [0] * 4), ser("sensor.s", [7] * 4), ser("sensor.pv", [540] * 4), ser("sensor.rd", [0] * 4), ser("sensor.rc", [140] * 4)]
    data = replay.build_data(cfg, raw, t0, t0 + 40, 10)
    assert data["units"][0]["rd"] == [400.0] * 4 and data["units"][0]["rc"] == [0.0] * 4        # 540 - 140 = 400 ins Haus


# ---------------- Geräte-Sensoren für die Auswahl ----------------
def test_sensoren_desselben_geraets_werden_gefunden():
    ha = HA("ws://x", "t")
    mk = lambda v, u="W", n="": {"state": str(v), "attributes": {"unit_of_measurement": u, "friendly_name": n}}
    p = "anker_solix_solarbank_4_e5000_pro_883_"
    ha.states = {
        f"number.{p}leistungssteuerung": mk(0),
        f"sensor.{p}solarleistung": mk(540, "W", "Solarleistung"),
        f"sensor.{p}ladestand": mk(7, "%", "Ladestand"),
        f"sensor.{p}batterieleistung": mk(-140),
        "sensor.anker_solix_solarbank_4_e5000_pro_999_solarleistung": mk(1),       # anderes Gerät
        "sensor.bitshake_leistung": mk(4),
    }
    out = ha.device_sensors(f"number.{p}leistungssteuerung")
    ids = [x["id"] for x in out]
    assert ids == [f"sensor.{p}batterieleistung", f"sensor.{p}ladestand", f"sensor.{p}solarleistung"]
    assert out[2]["name"] == "Solarleistung" and out[2]["state"] == "540" and out[2]["unit"] == "W"
    assert ha.device_sensors("") == [] and ha.device_sensors("number.kurz") == []

@pytest.mark.asyncio
async def test_endpunkt_geraetesensoren(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer
    import main as appmain
    from controller import ConfigStore, Controller
    store = ConfigStore(str(tmp_path / "c.json")); ctrl = Controller(None, store); ha = ctrl.ha = HA("ws://x", "t")
    ha.states = {"number.geraet_abc_leistung": {"state": "0", "attributes": {}},
                 "sensor.geraet_abc_solar": {"state": "540", "attributes": {"unit_of_measurement": "W"}},
                 "sensor.anderes_ding_x": {"state": "1", "attributes": {}}}
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        j = await (await c.get("/api/device_sensors?entity=number.geraet_abc_leistung")).json()
        assert [x["id"] for x in j] == ["sensor.geraet_abc_solar"]
