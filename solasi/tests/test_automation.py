import os, sys, tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import automation as A


def R(when, then=None, **kw):
    return {"id": kw.get("id", "a"), "name": "x", "enabled": True, "when": when, "then": then or {"kind": "notify", "text": "hi"}}


def ctx(**kw):
    c = {"minute": 480, "weekday": 0, "date": "2026-10-17", "soc": 50, "grid_w": 0, "pv_w": 0, "now": 1000.0}
    c.update(kw)
    return c


def test_bereinigen():
    r = A.clean_rules([{"id": "A B!", "when": {"kind": "time", "at": "7:5", "days": [9, "2"]}, "then": {"kind": "mode", "mode": "holiday"}},
                       {"when": {"kind": "soc_below", "value": 500}, "then": {"kind": "notify", "text": "x" * 500}},
                       {"when": {"kind": "kaputt"}, "then": {"kind": "notify"}}, "müll"])
    assert len(r) == 2 and r[0]["id"] == "ab" and r[0]["when"] == {"kind": "time", "at": "07:00", "days": [2]}
    assert r[1]["when"]["value"] == 100 and len(r[1]["then"]["text"]) == 200 and r[1]["id"] == "r2"
    assert A.clean_rules(None) == [] and len(A.clean_rules([R({"kind": "pv_above"})] * 50)) == A.MAX_RULES


def test_zeitplan_einmal_pro_tag():
    r = [R({"kind": "time", "at": "08:00", "days": [0]})]
    st = {}
    assert A.evaluate(r, ctx(minute=479), st) == []
    assert len(A.evaluate(r, ctx(minute=480), st)) == 1
    assert A.evaluate(r, ctx(minute=481), st) == []                     # schon heute ausgelöst
    assert len(A.evaluate(r, ctx(minute=481, date="2026-10-24"), st)) == 1
    assert A.evaluate(r, ctx(minute=700, date="2026-10-31"), {}) == []   # zu spät -> nicht nachholen
    assert A.evaluate(r, ctx(minute=480, weekday=1), {}) == []


def test_bedingungen_loesen_nur_beim_wechsel_aus():
    r = [R({"kind": "soc_below", "value": 20})]
    st = {}
    assert A.evaluate(r, ctx(soc=30), st) == []
    assert len(A.evaluate(r, ctx(soc=19), st)) == 1
    assert A.evaluate(r, ctx(soc=18), st) == []
    assert A.evaluate(r, ctx(soc=30), st) == [] and len(A.evaluate(r, ctx(soc=10), st)) == 1
    assert A.evaluate(r, ctx(soc=None), {}) == []
    off = [{**r[0], "enabled": False}]
    assert A.evaluate(off, ctx(soc=1), {}) == []


def test_netzbezug_mit_dauer():
    r = [R({"kind": "grid_above", "value": 2000, "minutes": 5})]
    st = {}
    assert A.evaluate(r, ctx(grid_w=2500, now=0), st) == []
    assert A.evaluate(r, ctx(grid_w=2500, now=200), st) == []
    assert len(A.evaluate(r, ctx(grid_w=2500, now=301), st)) == 1
    assert A.evaluate(r, ctx(grid_w=100, now=400), st) == [] and A.evaluate(r, ctx(grid_w=2500, now=410), st) == []   # Zeit beginnt neu


def test_beschreibung_und_bericht():
    d = A.describe(A.clean_rules([R({"kind": "time", "at": "22:00", "days": [0, 1, 2, 3, 4, 5, 6]}, {"kind": "mode", "mode": "care"})])[0], [{"id": "care", "name": "Akku schonen"}])
    assert d == "täglich um 22:00 Uhr: Modus „Akku schonen“ aktivieren"
    d2 = A.describe(A.clean_rules([R({"kind": "soc_below", "value": 20})])[0])
    assert d2.startswith("Wenn der Ladestand unter 20 %") and "melden: hi" in d2
    t, txt = A.weekly_report({"days": [], "total": {}})
    assert "keine Daten" in txt
    s = {"days": [{"date": "2026-10-12", "autarky": 0.6}, {"date": "2026-10-13", "autarky": 0.9}],
         "total": {"house": 70, "pv": 50, "imp": 20, "bat_dis": 15, "autarky": 0.71, "saved_eur": 17.5, "feedin_eur": 1.2}}
    t, txt = A.weekly_report(s)
    assert "71 %" in txt and "2026-10-13" in txt and "17.50 €" in txt


import asyncio, pytest
from controller import Controller, ConfigStore
from ha import HA


@pytest.mark.asyncio
async def test_regeln_im_regler(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    await ctrl.save_config({**store.cfg, "rules": [
        {"id": "low", "name": "Leer", "when": {"kind": "soc_below", "value": 20}, "then": {"kind": "mode", "mode": "emergency"}},
        {"id": "pv", "name": "Sonne", "when": {"kind": "pv_above", "value": 3000}, "then": {"kind": "notify", "text": "viel Sonne"}},
        {"id": "bad", "name": "Kaputt", "when": {"kind": "soc_above", "value": 90}, "then": {"kind": "mode", "mode": "gibtsnicht"}}]})
    assert [r["id"] for r in store.cfg["rules"]] == ["low", "pv", "bad"]
    snap = {"units": [{"soc": 15, "paused": False}, {"soc": 10}], "grid_w": 0, "pv_w": 3500, "extra_pv": 0, "has_pv": True}
    await ctrl._run_rules(snap)
    assert store.cfg["goals"]["mode"] == "emergency"
    msgs = [e["msg"] for e in ctrl.events]
    assert any("Regel „Sonne“: viel Sonne" in m for m in msgs) and any("Regel „Leer“" in m for m in msgs)
    n = len(ctrl.events)
    await ctrl._run_rules(snap)
    assert len(ctrl.events) == n                       # kein erneutes Auslösen
    snap["units"][0]["soc"] = snap["units"][1]["soc"] = 95
    await ctrl._run_rules(snap)
    assert any("gibt es nicht" in e["msg"] for e in ctrl.events)
