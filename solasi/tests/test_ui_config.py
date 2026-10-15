import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from controller import clean_order, clean_ui, deep_merge, DEFAULT_CONFIG


def test_default_leer():
    assert DEFAULT_CONFIG["ui"] == {"status_order": [], "status_hidden": [], "stats_order": [], "stats_hidden": []}


def test_clean_filtert_unbekannte_und_doppelte():
    u = clean_ui({"status_order": ["log", "log", "xx", 5, "kpis"], "status_hidden": ["trend"], "stats_order": "kaputt", "stats_hidden": ["tiles", "meters"]})
    assert u["status_order"] == ["log", "kpis"]
    assert u["status_hidden"] == ["trend"]
    assert u["stats_order"] == []
    assert u["stats_hidden"] == ["tiles"]


def test_clean_ohne_eingabe():
    assert clean_ui(None) == DEFAULT_CONFIG["ui"]
    assert clean_ui("x") == DEFAULT_CONFIG["ui"]


def test_merge_behaelt_gespeicherte_reihenfolge_und_alte_configs():
    m = deep_merge(DEFAULT_CONFIG, {"ui": {"status_order": ["log", "hero"]}})
    assert m["ui"]["status_order"] == ["log", "hero"] and m["ui"]["stats_order"] == []
    assert deep_merge(DEFAULT_CONFIG, {})["ui"]["status_hidden"] == []


def test_clean_order_kacheln():
    assert clean_order(["day", "m:sensor.x", "day", 3, "", None]) == ["day", "m:sensor.x"]
    assert clean_order("x") == [] and clean_order(None) == []
    assert DEFAULT_CONFIG["meters"]["order"] == []
