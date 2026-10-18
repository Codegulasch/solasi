import json, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["SOLASI_ALLOW_ALL"] = ""
from aiohttp.test_utils import TestClient, TestServer
import goals
import main as appmain
from controller import Controller, ConfigStore, DEFAULT_CONFIG
from ha import HA
import copy


def test_derive_ist_monoton_und_begrenzt():
    lo, hi = goals.derive({"reserve": 0, "precision": 0, "care": 0}), goals.derive({"reserve": 100, "precision": 100, "care": 100})
    assert lo["soc.min"] < hi["soc.min"] <= 95
    assert goals.derive({"reserve": 100, "care": 0})["soc.min"] == 45
    for g in ({"reserve": 100, "care": 100}, {"reserve": 0, "care": 100}, {}, {"reserve": "x", "precision": None}):
        d = goals.derive(g)
        assert 0 <= d["soc.min"] < d["soc.max"] <= 100 and d["control.min_gap"] >= 3 and d["control.offset_discharge"] >= 0
    assert goals.derive({"precision": 100})["control.offset_discharge"] == 0
    assert goals.clean({"reserve": 250, "precision": -5, "care": "x"}) == {"reserve": 100, "precision": 0, "care": 0}


def test_schaetzung_rundet_zurueck():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for g in ({"reserve": 62, "precision": 80, "care": 35}, {"reserve": 10, "precision": 90, "care": 10}):
        goals.apply(cfg, g)
        e = goals.estimate(cfg)
        assert abs(e["reserve"] - g["reserve"]) <= 6 and abs(e["precision"] - g["precision"]) <= 8 and abs(e["care"] - g["care"]) <= 6


def test_modus_aktiv_und_angepasst():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    assert goals.active_mode(cfg) is None                       # Standardwerte: kein reiner Modus
    goals.apply(cfg, goals.PRESETS[1], "autarky")
    assert goals.active_mode(cfg) == "autarky"
    cfg["soc"]["min"] += 3                                        # von Hand verändert
    assert goals.active_mode(cfg) is None
    rows = {r["path"]: r for r in goals.table(cfg)}
    assert rows["soc.min"]["custom"] is True and rows["soc.max"]["custom"] is False


@pytest.mark.asyncio
async def test_api_modi(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        snap = await (await c.get("/api/goals")).json()
        assert [m["id"] for m in snap["modes"]][:2] == ["balanced", "autarky"] and snap["mode"] is None
        r = await (await c.post("/api/goals/mode", json={"id": "emergency", "who": "Stefan"})).json()
        assert r["ok"] and r["mode"] == "emergency" and store.cfg["soc"]["min"] >= 45
        assert json.load(open(tmp_path / "s.json"))["goals"]["mode"] == "emergency"       # persistiert
        assert any("Notstrom" in e["msg"] and "Stefan" in e["msg"] for e in ctrl.events)
        st = await (await c.get("/api/status")).json()
        assert st["mode_id"] == "emergency"
        assert (await c.post("/api/goals/mode", json={"id": "gibtsnicht"})).status == 404
        p = await (await c.post("/api/goals/preview", json={"reserve": 0, "precision": 100, "care": 0})).json()
        assert p["derived"]["soc.min"] == 5 and store.cfg["soc"]["min"] >= 45                # Vorschau ändert nichts
        r = await (await c.post("/api/goals/set", json={"reserve": 40})).json()
        assert r["ok"] and r["goals"]["reserve"] == 40 and store.cfg["goals"]["reserve"] == 40 and store.cfg["goals"]["care"] is not None
        r = await (await c.post("/api/goals/custom", json={"name": "Wochenende", "icon": "🎣", "goals": {"reserve": 20, "precision": 60, "care": 40}})).json()
        assert r["ok"] and any(m.get("custom") and m["name"] == "Wochenende" for m in r["modes"])
        mid = r["id"]
        assert (await c.post("/api/goals/custom", json={"name": " "})).status == 400
        r = await (await c.delete(f"/api/goals/custom/{mid}")).json()
        assert not any(m.get("custom") for m in r["modes"])
        # ungültige Regler werden beim Speichern bereinigt
        cfg = await (await c.get("/api/config")).json()
        cfg["goals"] = {"mode": "x", "reserve": 900, "precision": None, "care": 5}
        assert (await c.post("/api/config", json=cfg)).status == 200
        assert store.cfg["goals"]["reserve"] == 100 and store.cfg["goals"]["precision"] is None


def test_wirkung_beschreibt_grenzen():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    goals.apply(cfg, goals.mode_by_id(cfg, "balanced"), "balanced")
    e = goals.effect(cfg, [{"name": "A", "soc": 5}, {"name": "B", "soc": 60}, {"name": "C", "soc": 97}, {"name": "D", "soc": -1}, {"name": "E", "soc": 50, "paused": True}])
    assert e["head"] == "Gibt ab bis 26 %, lädt bis 94 %"
    assert [(x["name"], x["state"]) for x in e["units"]] == [("A", "low"), ("B", "ok"), ("C", "full")]
    assert "unter 26 %" in e["units"][0]["text"] and "nicht aus dem Netz" in e["note"]
    snap = goals.snapshot(cfg)
    assert all("derived" in m for m in snap["modes"]) and snap["modes"][1]["derived"]["soc.min"] == 10
