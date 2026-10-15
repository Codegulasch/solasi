import asyncio, copy, json, os, sys, tempfile
from datetime import datetime, timezone
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
from controller import DEFAULT_CONFIG, Controller, ConfigStore, decide
from ha import HA
from stats import Stats
from learn import BaseLoadLearner, is_night
from notify import Notifier
import replay, selfcheck
from test_decide import mk_cfg, mk_unit, mk_snap


# ---------------- Statistik ----------------
def test_statistik_integriert_und_kennzahlen(tmp_path):
    day = {"d": datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)}
    st = Stats(str(tmp_path / "s.json"), clock=lambda: day["d"])
    t = 1000.0
    st.update(t, 2000, 1000, -1000, -1000)       # erster Aufruf nur Zeitmarke
    for _ in range(360):                          # 360 x 10 s = 1 h: PV 2 kW, Haus 1 kW, Einspeisung 1 kW, Speicher lädt 1 kW
        t += 10; st.update(t, 2000, 1000, -1000, -1000)
    s = st.summary(30)
    r = s["days"][0]
    assert r["date"] == "2026-10-04" and r["pv"] == 2.0 and r["house"] == 1.0 and r["exp"] == 1.0 and r["imp"] == 0 and r["bat_chg"] == 1.0
    assert r["autarky"] == 1.0 and r["selfcons"] == 0.5
    # Tageswechsel
    day["d"] = datetime(2026, 10, 5, 0, 5, tzinfo=timezone.utc)
    for _ in range(36):
        t += 10; st.update(t, 0, 500, 500, 0)
    s = st.summary(30, {"import_ct": 30, "feedin_ct": 10})
    assert [d["date"] for d in s["days"]] == ["2026-10-04", "2026-10-05"]
    assert s["days"][1]["imp"] == 0.05 and s["total"]["feedin_eur"] == 0.1 and s["total"]["saved_eur"] == 0.3 * 1.0 * 0 + round((1.05 - 0.05) * 0.3, 2)

def test_statistik_grosse_luecke_wird_gekappt_und_gespeichert(tmp_path):
    p = str(tmp_path / "s.json")
    st = Stats(p); st.update(0, None, None, 1000, None); st.update(3600, None, None, 1000, None)   # 1 h Lücke
    assert st.kpis(list(st.days.values())[0])["imp"] == round(1000 * 30 / 3600 / 1000, 3)
    st.save(); assert Stats(p).days == st.days


# ---------------- Grundlast lernen ----------------
def test_grundlast_lernen(tmp_path):
    L = BaseLoadLearner(str(tmp_path / "l.json"))
    assert L.value is None
    t = 0
    for night, watts in enumerate((200, 220, 180)):
        for _ in range(120):                       # 2 h Nachtdaten, 1 Messwert je Minute
            t += 60; L.observe(t, watts, True)
        L.observe(t + 60, 900, False)              # Morgen: Nacht wird abgeschlossen
    assert L.value == 200 and len(L.nights) == 3
    # kurze Nacht (< 1 h) zählt nicht
    for _ in range(20):
        t += 60; L.observe(t, 5000, True)
    L.observe(t + 60, 0, False)
    assert len(L.nights) == 3
    # Ausreißer-Nacht verfälscht den Median kaum
    for _ in range(120):
        t += 60; L.observe(t, 2000, True)
    L.observe(t + 60, 0, False)
    assert L.value == 210
    L.save(); assert BaseLoadLearner(str(tmp_path / "l.json")).value == 210

def test_vorlaeufiger_wert_aus_laufender_nacht(tmp_path):
    L = BaseLoadLearner(str(tmp_path / "l.json"))
    for i in range(40): L.observe(i * 60, 150, True)
    assert L.value == 150

def test_nacht_erkennung():
    assert is_night(5, None, 12) and not is_night(300, "below_horizon", 12)
    assert is_night(None, "below_horizon", 12) and not is_night(None, "above_horizon", 3)
    assert is_night(None, None, 3) and not is_night(None, None, 12)

def test_gelernte_grundlast_begrenzt_eco():
    cfg = mk_cfg(); cfg["soc"]["learn_base_load"] = True
    units = [mk_unit(cfg, 0, 30), mk_unit(cfg, 1, 30)]
    d = decide(cfg, mk_snap(cfg, 400, units, base_load=230))
    assert d["eco_active"] and d["t_target"] == 230


# ---------------- Benachrichtigungen ----------------
class FakeHA:
    def __init__(self): self.calls = []
    async def call_service(self, d, s, data): self.calls.append((d, s, data))

class FakeCtrl:
    def __init__(self, **notify):
        self.cfg = copy.deepcopy(DEFAULT_CONFIG); self.cfg["notify"].update(notify)
        self.ha = FakeHA(); self.events = []
    def event(self, level, msg): self.events.append((level, msg))

@pytest.mark.asyncio
async def test_meldung_nach_verzoegerung_mit_sperrzeit_und_entwarnung():
    c = FakeCtrl(service="notify.mobile_app_pixel", delay_min=2, cooldown_min=60)
    n = Notifier(c)
    await n.check({"meter": True}, now=0);   assert c.ha.calls == []          # noch in der Verzögerung
    await n.check({"meter": True}, now=100); assert c.ha.calls == []
    await n.check({"meter": True}, now=125); assert len(c.ha.calls) == 1       # nach 2 Minuten
    assert c.ha.calls[0][:2] == ("notify", "mobile_app_pixel") and "Zähler" in c.ha.calls[0][2]["title"]
    await n.check({"meter": True}, now=500); assert len(c.ha.calls) == 1       # nicht wiederholen
    await n.check({"meter": False}, now=600); assert len(c.ha.calls) == 2      # Entwarnung
    assert "behoben" in c.ha.calls[1][2]["title"]
    await n.check({"meter": True}, now=700); await n.check({"meter": True}, now=900)
    assert len(c.ha.calls) == 2                                               # Sperrzeit von 60 min gilt auch nach Entwarnung

@pytest.mark.asyncio
async def test_kurzer_ausfall_meldet_nichts():
    c = FakeCtrl(service="notify.x", delay_min=2); n = Notifier(c)
    await n.check({"meter": True}, now=0); await n.check({"meter": False}, now=60)
    assert c.ha.calls == []

@pytest.mark.asyncio
async def test_ereignis_abschaltbar_und_persistent_notification():
    c = FakeCtrl(service="persistent_notification", delay_min=0); c.cfg["notify"]["events"]["empty"] = False
    n = Notifier(c)
    await n.check({"empty": True, "offline": True}, now=0)
    assert [x[2].get("notification_id") for x in c.ha.calls] == ["solasi_offline"]
    assert c.ha.calls[0][:2] == ("persistent_notification", "create")

@pytest.mark.asyncio
async def test_ohne_ziel_keine_meldung():
    c = FakeCtrl(service="", delay_min=0); await Notifier(c).check({"meter": True}, now=0); assert c.ha.calls == []


# ---------------- Abregelungs-Selbsttest ----------------
def mk_ctrl(tmp_path):
    store = ConfigStore(str(tmp_path / "c.json"))
    ctrl = Controller(None, store); ctrl.ha = HA("ws://x", "t"); return ctrl

def snap_full(cfg, grid, pv=1500):
    units = [mk_unit(cfg, 0, 100), mk_unit(cfg, 1, 100)]
    return mk_snap(cfg, grid, units, pv_w=float(pv), has_pv=True)

def test_abregelung_versagt_und_erholt_sich(tmp_path):
    ctrl = mk_ctrl(tmp_path); cfg = ctrl.cfg
    d = {"meter_ok": True}
    for t in range(0, 200, 10):
        ctrl._curtail_update(snap_full(cfg, -300), d, t)       # Einspeisung 300 W trotz vollem Speicher
    assert ctrl.curtail["state"] == "fehlgeschlagen" and ctrl.curtail["export_w"] == 300
    assert ctrl._problems(snap_full(cfg, -300), {"meter_ok": True})["curtail"] is True
    for t in range(200, 900, 10):
        ctrl._curtail_update(snap_full(cfg, 0), d, t)           # wieder ausgeglichen
    assert ctrl.curtail["state"] == "ok"

def test_abregelung_ok_bei_ausgeglichenem_zaehler(tmp_path):
    ctrl = mk_ctrl(tmp_path); cfg = ctrl.cfg
    for t in range(0, 200, 10):
        ctrl._curtail_update(snap_full(cfg, 5), {"meter_ok": True}, t)
    assert ctrl.curtail["state"] == "ok"

def test_abregelung_nachts_oder_nicht_voll_keine_beurteilung(tmp_path):
    ctrl = mk_ctrl(tmp_path); cfg = ctrl.cfg
    for t in range(0, 400, 10):
        ctrl._curtail_update(snap_full(cfg, -300, pv=20), {"meter_ok": True}, t)     # keine Sonne
        s = snap_full(cfg, -300); s["units"][0]["soc"] = 80
        ctrl._curtail_update(s, {"meter_ok": True}, t)                               # nicht alle voll
    assert ctrl.curtail["state"] == "unbekannt"

def test_kurze_einspeisung_loest_nicht_aus(tmp_path):
    ctrl = mk_ctrl(tmp_path); cfg = ctrl.cfg
    for t in range(0, 60, 10): ctrl._curtail_update(snap_full(cfg, -300), {"meter_ok": True}, t)
    for t in range(60, 400, 10): ctrl._curtail_update(snap_full(cfg, 0), {"meter_ok": True}, t)
    assert ctrl.curtail["state"] == "ok"


# ---------------- Systemprüfung ----------------
def test_systempruefung_findet_probleme(tmp_path):
    ctrl = mk_ctrl(tmp_path); cfg = ctrl.cfg; ha = ctrl.ha
    ha.connected = True
    ha.states = {
        "sensor.grid": {"state": "120", "attributes": {"unit_of_measurement": "kW"}},
        "number.a": {"state": "unavailable", "attributes": {"max": 600}},
        "select.dir": {"state": "discharge", "attributes": {"options": ["charge", "discharge"]}},
        "select.mode": {"state": "self_consumption", "attributes": {"options": ["self_consumption", "smart"]}},
        "sensor.soc": {"state": "130", "attributes": {}},
    }
    cfg["grid"]["entity"] = "sensor.grid"
    u = cfg["units"][0]; u.update(num="number.a", dir="select.dir", mode="select.mode", soc="sensor.soc", real_dis="sensor.fehlt", max_dis=800)
    r = selfcheck.run(cfg, ha, ctrl)
    byitem = {(i["area"], i["item"]): i for i in r["items"]}
    assert byitem[("Zähler", "Netzleistung")]["status"] == "warn" and "kW" in byitem[("Zähler", "Netzleistung")]["text"]
    assert byitem[("Speicher A", "Leistung (number)")]["status"] == "warn" and "third_party_control" in byitem[("Speicher A", "Leistung (number)")]["hint"]
    assert byitem[("Speicher A", "Max. Entladeleistung")]["status"] == "warn"
    assert byitem[("Speicher A", "Modus-Option")]["status"] == "error"          # third_party_control fehlt
    assert byitem[("Speicher A", "Richtungs-Optionen")]["status"] == "ok"
    assert byitem[("Speicher A", "SOC-Wert")]["status"] == "warn"
    assert byitem[("Speicher A", "Echte Entladeleistung")]["status"] == "error"   # Entität existiert nicht
    assert r["summary"]["error"] >= 2 and r["summary"]["ok"] >= 3

def test_systempruefung_ohne_konfiguration(tmp_path):
    ctrl = mk_ctrl(tmp_path); r = selfcheck.run(ctrl.cfg, ctrl.ha, ctrl)
    assert any(i["status"] == "error" and i["item"] == "Konfiguration" for i in r["items"])


# ---------------- Replay ----------------
def test_ueberschreibungen_werden_geprueft():
    cfg = mk_cfg()
    out = replay.apply_overrides(cfg, {"control.min_gap": "8", "features.eco": 0, "soc.min": 20, "control.split": "equal"})
    assert out["control"]["min_gap"] == 8.0 and out["features"]["eco"] is False and out["soc"]["min"] == 20.0 and cfg["control"]["min_gap"] == 5
    for bad in ({"units.0.num": "x"}, {"soc.min": 500}, {"control.split": "zufall"}):
        with pytest.raises(ValueError): replay.apply_overrides(cfg, bad)

def test_historie_wird_gelesen_und_aufgefuellt():
    raw = [[{"entity_id": "sensor.g", "state": "100", "last_changed": "1970-01-01T00:00:00+00:00"},
            {"state": "unavailable", "last_changed": "1970-01-01T00:00:25+00:00"},
            {"state": "300", "last_changed": "1970-01-01T00:00:45+00:00"}]]
    r = replay.resample(replay.parse_history(raw), 0, 60, 10)["sensor.g"]
    assert r == [100.0, 100.0, 100.0, 100.0, 100.0, 300.0]       # "unavailable" hält den letzten Wert

def synth(cfg, hours=1, load=500.0, pv=0.0, grid=None, soc=(80.0, 60.0), step=10):
    n = int(hours * 3600 // step)
    units = [mk_unit(cfg, i, 0)["cfg"] for i in range(2)]
    u = lambda i: {"cfg": units[i], "soc": [soc[i]] * n, "rd": [0.0] * n, "rc": [0.0] * n, "pv": [pv / 2] * n}
    return {"t0": 0, "step": step, "n": n, "grid": [load] * n if grid is None else grid, "extra": None, "house": None, "units": [u(0), u(1)]}

def test_simulation_nulleinspeisung_konstante_last():
    cfg = mk_cfg(); cfg["control"]["total_max_dis"] = 2000
    r = replay.simulate(cfg, synth(cfg, hours=2, load=500.0, soc=(80.0, 60.0)))
    assert r["exp"] < 0.02                              # praktisch keine Einspeisung
    assert r["imp"] < 0.12                              # Netzbezug nur Einschwingen + Offset (10 W)
    assert r["bat_dis"] > 0.85 and r["end_soc"] < 70    # Speicher deckt den Bedarf und entlädt sich

def test_simulation_leerer_speicher_deckt_nichts():
    cfg = mk_cfg()
    r = replay.simulate(cfg, synth(cfg, hours=1, load=500.0, soc=(5.0, 5.0)))
    assert r["imp"] > 0.45 and r["bat_dis"] == 0

def test_simulation_voller_speicher_bypass_gegen_abregelung():
    cfg = mk_cfg()
    d = synth(cfg, hours=1, load=300.0, pv=1500.0, soc=(100.0, 100.0))
    d["grid"] = [300.0 - 1500.0] * d["n"]               # Historie: PV deckt Haus, Rest geht ins Netz
    bypass = replay.simulate(cfg, d, curtail=False)
    gedrosselt = replay.simulate(cfg, d, curtail=True)
    assert bypass["exp"] > 0.5                          # Annahme: Firmware reicht PV ungedrosselt durch
    assert gedrosselt["exp"] < 0.1 and gedrosselt["curtailed"] > 0.5      # Annahme: Firmware drosselt

def test_eco_im_replay_begrenzt_entladung():
    cfg = mk_cfg(); cfg["control"]["total_max_dis"] = 2000
    d = synth(cfg, hours=1, load=800.0, soc=(30.0, 30.0))
    eco = replay.simulate(cfg, d)
    cfg2 = replay.apply_overrides(cfg, {"features.eco": False})
    noeco = replay.simulate(cfg2, d)
    assert eco["eco_h"] > 0.9 and eco["bat_dis"] < noeco["bat_dis"] - 0.3 and eco["imp"] > noeco["imp"] + 0.3

def test_anforderungen():
    cfg = mk_cfg(); assert "Netzsensor" in replay.check_requirements(cfg)
    cfg["grid"]["entity"] = "sensor.g"; u = cfg["units"][0]; u.update(num="number.a", dir="select.d", soc="sensor.s")
    miss = replay.check_requirements(cfg)
    assert any("echte Entladeleistung" in m for m in miss) and any("PV-Leistung" in m for m in miss)


# ---------------- Tagesverlauf für die Karte ----------------
def test_trend_mittelt_je_fuenf_minuten_und_begrenzt(tmp_path):
    ctrl = mk_ctrl(tmp_path); ctrl.trend_every = 0; ctrl.trend_keep = 3
    for i in range(5):
        ctrl._trend_add(100 * i, 300)
    assert len(ctrl.trend) == 3 and ctrl.trend[-1][1:] == [400, 300]
    ctrl.trend_every = 300
    ctrl._trend_add(None, None)                       # fehlende Werte brechen nichts
    assert len(ctrl.trend) == 3


def test_trend_series_hat_zeitstempel(tmp_path):
    ctrl = mk_ctrl(tmp_path); ctrl.trend_every = 0; ctrl.trend = []
    ctrl._trend_add(100, 300); ctrl._trend_add(200, 310)
    s = ctrl.trend_series()
    assert len(s["t"]) == len(s["pv"]) == len(s["house"]) == 2 and s["pv"] == [100, 200]
