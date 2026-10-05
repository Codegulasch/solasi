"""Energiefluss: Verteilung der Leistungen auf die Linien der Grafik."""
import os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
from energy import flows
from test_drivers import boot
from test_flows import ANKER, SCREENSHOT
from test_integration import stop, wait_for


def balance(f):
    """Hausverbrauch aus den Linien (Probe)."""
    return (f["solar_house"] + max(f["battery_house"], 0) + max(f["grid_house"], 0)
            - max(-f["grid_house"], 0) - max(-f["battery_house"], 0))


def test_gemeldeter_fall_solar_haus_und_ueberschuss_in_den_speicher():
    """780 W Solar, Speicher lädt 260 W, Netz 9 W Bezug -> 520 W ins Haus, 260 W in den Speicher."""
    f = flows(780, -260, 9)
    assert f == {"solar_house": 520, "solar_battery": 260, "battery_house": 0, "grid_house": 9}
    assert balance(f) == 529                                   # = Haus laut Anzeige

def test_anker_app_beispiel():
    assert flows(540, -140, 0) == {"solar_house": 400, "solar_battery": 140, "battery_house": 0, "grid_house": 0}

def test_nachts_speicher_entlaedt():
    f = flows(0, 300, 100)
    assert f == {"solar_house": 0, "solar_battery": 0, "battery_house": 300, "grid_house": 100} and balance(f) == 400

def test_tagsueber_solar_und_speicher_zusammen():
    f = flows(300, 200, 0)
    assert f["solar_house"] == 300 and f["battery_house"] == 200 and f["solar_battery"] == 0 and balance(f) == 500

def test_netzladen_nachts_laeuft_ueber_das_haus():
    f = flows(0, -600, 700)
    assert f == {"solar_house": 0, "solar_battery": 0, "battery_house": -600, "grid_house": 700} and balance(f) == 100

def test_netzladen_zusaetzlich_zur_pv():
    f = flows(200, -600, 500)                                  # PV lädt 200 W, 400 W kommen aus dem Netz
    assert f == {"solar_house": 0, "solar_battery": 200, "battery_house": -400, "grid_house": 500} and balance(f) == 100

def test_einspeisung_bei_vollem_speicher():
    f = flows(1500, 0, -700)
    assert f["solar_house"] == 1500 and f["solar_battery"] == 0 and f["grid_house"] == -700 and balance(f) == 800

def test_unbekannte_werte_bleiben_unbekannt():
    assert flows(None, -140, 4) == {"solar_house": None, "solar_battery": None, "battery_house": -140, "grid_house": 4}
    assert flows(540, None, 4) == {"solar_house": None, "solar_battery": None, "battery_house": None, "grid_house": 4}
    assert flows(None, None, None)["grid_house"] is None

def test_rauschen_und_negative_pv():
    f = flows(-3, 0, 0)
    assert f["solar_house"] == 0 and f["solar_battery"] == 0

@pytest.mark.asyncio
async def test_status_und_entitaet_enthalten_die_flusswerte(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], SCREENSHOT)          # Solar 540 W, Batterie lädt 140 W
    m.set_state("sensor.grid", 0)
    ctrl.cfg["enabled"] = False
    try:
        assert await wait_for(lambda: (ctrl.status.get("flows") or {}).get("solar_battery") == 140, 8), ctrl.status.get("flows")
        f = ctrl.status["flows"]
        assert f["solar_house"] == 400 and f["battery_house"] == 0 and f["grid_house"] == 0
        assert ctrl._entity_payloads()["sensor.solasi"][1]["flows"] == f
    finally:
        await stop(m, tasks)
