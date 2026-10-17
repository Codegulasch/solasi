import os, sys, tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import discover


def ent(eid, name, state="1", **attrs):
    return eid, {"entity_id": eid, "state": state, "attributes": {"friendly_name": name, **attrs}}


STATES = dict([
    ent("number.huette_ls", "Anker Solix 4 HÜTTE Leistungssteuerung", "0"),
    ent("select.huette_lf", "Anker Solix 4 HÜTTE Leistungsfluss", "idle"),
    ent("select.huette_bm", "Anker Solix 4 HÜTTE Betriebsmodus", "third_party_control"),
    ent("sensor.huette_soc", "Anker Solix 4 HÜTTE Ladestand", "100", unit_of_measurement="%"),
    ent("sensor.huette_pv", "Anker Solix 4 HÜTTE Solarleistung", "340", unit_of_measurement="W"),
    ent("number.huette_np", "Anker Solix 4 HÜTTE Notstromreserve", "20"),
    ent("number.huette_np2", "Anker Solix 4 HÜTTE Notstrom Ladestand", "20"),
    ent("number.huette_eg", "Anker Solix 4 HÜTTE Entladegrenze", "10"),
    ent("number.huette_lo", "Anker Solix 4 HÜTTE Ladeobergrenze", "100"),
    ent("number.dach_ls", "Anker Solix 4 DACH Leistungssteuerung", "0"),
    ent("select.dach_lf", "Anker Solix 4 DACH Leistungsfluss", "idle"),
    ent("sensor.dach_soc", "Anker Solix 4 DACH Ladestand", "40"),
    # englisch, anderes Gerät
    ent("number.sb_pc", "Garage Battery Power Control", "0"),
    ent("sensor.sb_soc", "Garage Battery State of Charge", "55"),
    ent("sensor.shelly_total", "Shelly 3EM Netz Gesamtleistung", "-120", unit_of_measurement="W"),
    ent("sensor.kitchen", "Küche Temperatur", "21", unit_of_measurement="°C"),
    ent("sensor.pv_total", "PV Gesamt", "800", unit_of_measurement="W"),
    ent("sensor.zaehler_kwh", "Netzbezug Zählerstand", "123", unit_of_measurement="kWh"),
])


def test_geraete_werden_gruppiert():
    us = {u["name"]: u for u in discover.find_units(STATES)}
    assert set(us) == {"Anker Solix 4 HÜTTE", "Anker Solix 4 DACH", "Garage Battery"}
    h = us["Anker Solix 4 HÜTTE"]
    assert (h["driver"], h["num"], h["dir"], h["mode"], h["soc"], h["pv"]) == ("anker", "number.huette_ls", "select.huette_lf", "select.huette_bm", "sensor.huette_soc", "sensor.huette_pv")
    assert h["lim_res"] == "number.huette_np" and h["lim_dis"] == "number.huette_eg" and h["lim_chg"] == "number.huette_lo"   # kürzerer Name gewinnt
    d = us["Anker Solix 4 DACH"]
    assert d["soc"] == "sensor.dach_soc" and d["lim_res"] == "" and d["pv"] == ""
    g = us["Garage Battery"]
    assert g["driver"] == "signed" and g["num"] == "number.sb_pc" and g["dir"] == ""        # nur eine Zahl -> Zahl mit Vorzeichen


def test_bereits_eingerichtete_werden_markiert():
    us = {u["name"]: u for u in discover.find_units(STATES, ["number.huette_ls"])}
    assert us["Anker Solix 4 HÜTTE"]["configured"] is True and us["Anker Solix 4 DACH"]["configured"] is False


def test_netz_kandidaten():
    g = discover.find_grid(STATES)
    assert [x["id"] for x in g] == ["sensor.shelly_total"]      # kWh und Temperatur zählen nicht, „PV Gesamt“ passt nicht auf Netz
    assert discover.find_units({}) == [] and discover.find_grid({}) == []
    r = discover.discover(STATES, {"units": [{"num": "number.dach_ls"}], "grid": {"entity": "sensor.x"}})
    assert r["grid_set"] is True and {u["name"]: u["configured"] for u in r["units"]}["Anker Solix 4 DACH"] is True
