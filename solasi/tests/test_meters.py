import os, sys, tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from meters import Meters
from test_features import mk_ctrl


def look(table):
    return lambda eid: table.get(eid)


def test_tageswert_ist_differenz_zum_ersten_wert_des_tages(tmp_path):
    m = Meters(str(tmp_path / "m.json"))
    it = [{"entity": "sensor.w", "name": "Wasser Haus", "icon": "wasser", "color": "water"}]
    assert m.compute(it, look({"sensor.w": ("552.62", "m³", "x")}), "2026-10-15")[0]["day"] == 0
    r = m.compute(it, look({"sensor.w": ("552.80", "m³", "x")}), "2026-10-15")[0]
    assert r["day"] == 0.18 and r["dec"] == 2 and r["unit"] == "m³" and r["name"] == "Wasser Haus" and r["icon"] == "wasser"


def test_neuer_tag_setzt_den_stand_neu(tmp_path):
    m = Meters(str(tmp_path / "m.json"))
    it = [{"entity": "sensor.s"}]
    m.compute(it, look({"sensor.s": ("100.0", "kWh", "Strom")}), "2026-10-15")
    assert m.compute(it, look({"sensor.s": ("104.6", "kWh", "Strom")}), "2026-10-15")[0]["day"] == 4.6
    assert m.compute(it, look({"sensor.s": ("105.0", "kWh", "Strom")}), "2026-10-16")[0]["day"] == 0


def test_stand_bleibt_nach_neustart_erhalten(tmp_path):
    p = str(tmp_path / "m.json")
    it = [{"entity": "sensor.s"}]
    Meters(p).compute(it, look({"sensor.s": ("10", "kWh", "")}), "2026-10-15")
    assert Meters(p).compute(it, look({"sensor.s": ("12.5", "kWh", "")}), "2026-10-15")[0]["day"] == 2.5


def test_zaehler_getauscht_oder_zurueckgesetzt_gibt_keinen_negativen_wert(tmp_path):
    m = Meters(str(tmp_path / "m.json"))
    it = [{"entity": "sensor.s"}]
    m.compute(it, look({"sensor.s": ("500", "kWh", "")}), "2026-10-15")
    assert m.compute(it, look({"sensor.s": ("3", "kWh", "")}), "2026-10-15")[0]["day"] == 0


def test_nicht_verfuegbar_und_fehlende_entitaet(tmp_path):
    m = Meters(str(tmp_path / "m.json"))
    out = m.compute([{"entity": "sensor.a"}, {"entity": "sensor.b"}, {"entity": ""}],
                    look({"sensor.a": (None, "m³", "A")}), "2026-10-15")
    assert len(out) == 2 and out[0]["value"] is None and out[0]["day"] is None and out[1]["value"] is None


def test_unbekanntes_symbol_und_farbe_fallen_auf_standard_zurueck_und_daily_aus(tmp_path):
    m = Meters(str(tmp_path / "m.json"))
    r = m.compute([{"entity": "sensor.a", "icon": "<x>", "color": "rot", "daily": False}], look({"sensor.a": ("1", "", "")}), "2026-10-15")[0]
    assert r["icon"] == "zaehler" and r["color"] == "zaehl" and r["day"] is None


def test_controller_liefert_zaehler_und_tageswerte(tmp_path):
    ctrl = mk_ctrl(tmp_path)
    ctrl.meters = Meters(str(tmp_path / "mm.json"))
    ctrl.cfg["meters"] = {"show_day": True, "extra": False, "items": [{"entity": "sensor.s", "name": "Strom", "icon": "zaehler", "color": "zaehl", "daily": True}]}
    ctrl.ha.states["sensor.s"] = {"state": "13141.74", "attributes": {"unit_of_measurement": "kWh", "friendly_name": "Zählerstand"}}
    v = ctrl.meter_view()
    assert v["items"][0]["value"] == 13141.74 and v["items"][0]["unit"] == "kWh" and v["show_day"] is True
    assert "autarky" in (v["today"] or {"autarky": None})
