import copy, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from controller import DEFAULT_CONFIG, decide, surplus_value

def mk_cfg(**ctrl):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["control"]["total_max_dis"] = 2000
    cfg["control"].update(ctrl)
    return cfg

def mk_unit(cfg, i, soc, setv=0.0, has=True, real=0.0):
    return {"cfg": cfg["units"][i], "k": f"U{i}", "has": has, "soc": soc, "set": setv,
            "real": real, "dir": "discharge", "num_state": "0", "mode": None}

def mk_snap(cfg, grid, units, meter_ok=True, slots=None, **kw):
    s = {"meter_ok": meter_ok, "grid_w": grid, "units": units,
         "slots": slots or [{"ent_state": None, "num_v": None, "pwr_w": None}] * 3,
         "out_w": 0.0, "has_out": False, "pv_w": 0.0, "has_pv": False, "extra_pv": 0.0,
         "house_w": None, "custom_w": None}
    s.update(kw)
    return s

def run(grid, socs, sets=(0, 0), cfg=None, **kw):
    cfg = cfg or mk_cfg()
    units = [mk_unit(cfg, i, soc, sets[i]) for i, soc in enumerate(socs)]
    d = decide(cfg, mk_snap(cfg, grid, units, **kw))
    return cfg, units, d

def test_bezug_split_nach_soc():
    _, u, d = run(400, (80, 40))
    assert d["want_dis"] and d["t_target"] == 390
    assert [x["p"] for x in u] == [280, 110]          # identisch mit dem Blueprint-Test

def test_sequential_zweites_geraet_erst_bei_bedarf():
    cfg = mk_cfg(split="sequential"); cfg["units"][0]["max_dis"] = 300
    _, u, d = run(400, (80, 40), cfg=cfg)
    assert u[0]["p"] == 300 and u[1]["p"] == 90

def test_einspeisung_laedt():
    _, u, d = run(-500, (80, 40))
    assert d["want_chg"] and d["t_target"] == -500
    assert u[0]["p"] < 0 and u[1]["p"] < 0 and u[1]["p"] < u[0]["p"]   # leereres Gerät lädt mehr
    assert abs(sum(x["p"] for x in u) + 500) <= 10

def test_unter_schwelle_nichts():
    _, u, d = run(60, (80, 40))
    assert d["t_target"] == 0 and all(x["p"] == 0 for x in u)

def test_hysterese_laufendes_geraet_bleibt_unter_einschaltschwelle():
    # läuft bereits (set 100), Bilanz 100+60=160 >= 80 (Ausschalt-Schwelle) -> weiter regeln
    _, u, d = run(60, (80, 40), sets=(100, 0))
    assert d["want_dis"]

def test_beide_leer():
    _, u, d = run(400, (10, 12))
    assert not d["want_dis"] and d["eco_active"] and all(x["p"] == 0 for x in u)

def test_eco_begrenzt_gesamt():
    _, u, d = run(400, (30, 30))
    assert d["eco_active"] and d["t_target"] == 150
    assert sum(x["p"] for x in u) <= 160

def test_eco_ausschaltbar():
    cfg = mk_cfg(); cfg["features"]["eco"] = False
    _, u, d = run(400, (30, 30), cfg=cfg)
    assert not d["eco_active"] and d["t_target"] == 390

def test_voll_erzwingt_abregelung():
    _, u, d = run(0, (100, 100))
    assert all(x["force"] and x["p"] == 0 for x in u)

def test_voll_abregelung_ausschaltbar():
    cfg = mk_cfg(); cfg["features"]["strict_zero"] = False
    _, u, d = run(0, (100, 100), cfg=cfg)
    assert not any(x["force"] for x in u)

def test_ac_laden_ausschaltbar():
    cfg = mk_cfg(); cfg["features"]["ac_charge"] = False
    _, u, d = run(-500, (50, 50), cfg=cfg)
    assert not d["want_chg"] and all(x["p"] == 0 for x in u)

def test_zaehlerausfall_setzt_null():
    _, u, d = run(400, (80, 40), meter_ok=False)
    assert all(x["p"] == 0 for x in u)

def test_ein_geraet_genuegt():
    cfg = mk_cfg()
    units = [mk_unit(cfg, 0, 70)]
    d = decide(cfg, mk_snap(cfg, 300, units))
    assert units[0]["p"] == 290

def test_aufgenommene_leistung_zaehlt_zur_bilanz():
    # Geräte liefern schon 200+100, Netz zeigt 300 -> Hausbedarf 600
    _, u, d = run(300, (80, 40), sets=(200, 100))
    assert d["net_balance"] == 600 and d["t_target"] == 590

def test_schwellen_ausschaltbar():
    cfg = mk_cfg(); cfg["features"]["thresholds"] = False
    _, u, d = run(30, (80, 40), cfg=cfg)
    assert d["want_dis"] and d["t_target"] == 20

def test_entladesperre_wallbox():
    cfg = mk_cfg()
    cfg["surplus"]["enabled"] = True
    cfg["surplus"]["slots"][0].update(ent="switch.wb", block=True, pmax=1400)
    slots = [{"ent_state": "on", "num_v": None, "pwr_w": None}] + [{"ent_state": None, "num_v": None, "pwr_w": None}] * 2
    units = [mk_unit(cfg, 0, 80), mk_unit(cfg, 1, 80)]
    d = decide(cfg, mk_snap(cfg, 1700, units, slots=slots))   # Haus 300 + Wallbox 1400
    assert d["blocked_w"] == 1400 and d["net_dis"] == 300
    assert d["t_target"] == 290                                # nur das Haus, nicht die Wallbox
    d2 = decide(cfg, mk_snap(cfg, 1700, [mk_unit(cfg,0,80), mk_unit(cfg,1,80)],
                             slots=[{"ent_state": "off", "num_v": None, "pwr_w": None}] * 3))
    assert d2["blocked_w"] == 0 and d2["t_target"] == 1600   # ohne Sperre: Geräte-Limit 2 x 800 W

def test_sperre_wirkt_nicht_auf_laden():
    cfg = mk_cfg(); cfg["surplus"]["enabled"] = True
    cfg["surplus"]["slots"][0].update(ent="switch.wb", block=True, pmax=1400)
    slots = [{"ent_state": "on", "num_v": None, "pwr_w": None}] + [{"ent_state": None, "num_v": None, "pwr_w": None}] * 2
    d = decide(cfg, mk_snap(cfg, -300, [mk_unit(cfg, 0, 50), mk_unit(cfg, 1, 50)], slots=slots))
    assert d["net_balance"] == -300 and d["want_chg"] and d["t_target"] == -300

def test_ueberschuss_pv_modus():
    cfg = mk_cfg(); cfg["surplus"]["source"] = "pv"
    snap = mk_snap(cfg, -100, [], pv_w=3000, has_pv=True, out_w=1100, has_out=True)
    assert surplus_value(cfg, snap) == 2000      # Haus 1000 W, PV 3000 W

def test_ueberschuss_rueckfall_auf_netz():
    cfg = mk_cfg(); cfg["surplus"]["source"] = "pv"
    snap = mk_snap(cfg, -400, [])
    assert surplus_value(cfg, snap) == 400

def test_ueberschuss_eigener_sensor():
    cfg = mk_cfg(); cfg["surplus"]["source"] = "custom"
    assert surplus_value(cfg, mk_snap(cfg, 0, [], custom_w=450.0)) == 450.0

def test_entitaetsmaximum_begrenzt_und_rest_geht_ans_andere_geraet():
    # Speicher A darf laut Entität nur 800 W, obwohl max_dis 1250 eingestellt ist: der Rest muss von B kommen
    cfg = mk_cfg(); cfg["units"][0]["max_dis"] = 1250; cfg["units"][1]["max_dis"] = 800
    units = [mk_unit(cfg, 0, 80), mk_unit(cfg, 1, 80)]
    units[0]["nmax_dis"] = 800
    d = decide(cfg, mk_snap(cfg, 2000, units))
    assert units[0]["p"] == 800 and units[1]["p"] == 800
