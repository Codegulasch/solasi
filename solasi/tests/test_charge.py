import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import charge
from test_decide import mk_cfg, mk_unit, mk_snap
from controller import decide


def job(**kw):
    return charge.clean_job({"target": 50, **kw})


def go(socs, j, grid=300, cfg=None, **kw):
    cfg = cfg or mk_cfg()
    units = [mk_unit(cfg, i, s) for i, s in enumerate(socs)]
    d = decide(cfg, mk_snap(cfg, grid, units, charge=j, **kw))
    return cfg, units, d


def test_clean_job():
    assert charge.clean_job({"target": 0}) is not None and charge.clean_job({"target": 0})["target"] == 1
    assert charge.clean_job({"target": "x"}) is None
    assert charge.clean_job("x") is None
    j = charge.clean_job({"target": 500, "power_w": -5, "units": ["A", 3], "order": "kaputt"}, {"A"})
    assert j["target"] == 100 and j["power_w"] == 0 and j["units"] == ["A"] and j["order"] == ""


def test_clean_charge():
    assert charge.clean_charge({"order": "x", "max_w": "abc"}) == {"order": "low", "max_w": 0}
    assert charge.clean_charge({"order": "parallel", "max_w": 1500})["max_w"] == 1500


def test_laedt_aus_netz_trotz_bezug():
    cfg, u, d = go([10, 80], job(units=["U0"]))
    assert u[0]["p"] < 0                     # lädt, obwohl Netzbezug herrscht
    assert u[1]["p"] >= 0


def test_ohne_job_kein_netzladen():
    cfg, u, d = go([10, 80], None)
    assert u[0]["p"] >= 0


def test_ziel_erreicht_laedt_nicht_mehr():
    cfg, u, d = go([55, 60], job())
    assert u[0]["p"] >= 0 and u[1]["p"] >= 0


def test_reihenfolge_niedrigster_zuerst_mit_gesamtleistung():
    cfg = mk_cfg()
    cfg["units"][0]["max_chg"] = cfg["units"][1]["max_chg"] = 800
    _, u, d = go([30, 10], job(power_w=800), cfg=cfg)
    assert u[1]["p"] == -800 and u[0]["p"] >= 0     # U1 ist leerer


def test_reihenfolge_liste_und_hoechster():
    cfg = mk_cfg()
    _, u, _ = go([30, 10], job(power_w=800, order="list"), cfg=cfg)
    assert u[0]["p"] == -800 and u[1]["p"] >= 0
    _, u, _ = go([30, 10], job(power_w=800, order="high"), cfg=cfg)
    assert u[0]["p"] == -800


def test_parallel_teilt():
    cfg = mk_cfg()
    _, u, _ = go([30, 10], job(power_w=800, order="parallel"), cfg=cfg)
    assert u[0]["p"] == -400 and u[1]["p"] == -400


def test_einstellung_reihenfolge_gilt_ohne_job_reihenfolge():
    cfg = mk_cfg()
    cfg["charge"] = {"order": "list", "max_w": 600}
    _, u, _ = go([30, 10], job(), cfg=cfg)
    assert u[0]["p"] == -600 and u[1]["p"] >= 0


def test_ladeobergrenze_im_speicher_wird_ueberstimmt():
    cfg = mk_cfg()
    units = [mk_unit(cfg, 0, 10)]
    units[0]["lim_chg"] = 20
    d = decide(cfg, mk_snap(cfg, 100, units, charge=job(target=60)))
    assert units[0]["max"] == 60 and units[0]["p"] < 0


def test_sicherungsgrenze_deckelt():
    cfg = mk_cfg()
    _, u, _ = go([10, 80], job(units=["U0"]), charge_caps={"U0": 300})
    assert -300 <= u[0]["p"] <= -250


def test_zaehler_ausgefallen_kein_laden():
    cfg, u, d = go([10, 80], job(), meter_ok=False)
    assert u[0]["p"] == 0


def test_schaetzung():
    cfg = mk_cfg()
    units = [mk_unit(cfg, 0, 20)]
    units[0].update(cap=5.0, ccap_job=1000)
    e = charge.estimate(job(target=60), units, cfg)
    assert e["kwh"] == 2.0 and 2.0 < e["hours"] < 2.5 and e["power_w"] == 1000


def test_headroom():
    pv = {"loads": {"L1": 10.0}, "feed_units": [{"name": "A", "phase": "L1"}]}
    u = [{"k": "A", "ac": -690}]
    c = charge.headroom_caps(pv, u, 16)
    assert round(c["A"]) == round((16 * 0.95 - (10 - 3)) * 230)
    assert charge.headroom_caps(pv, u, 0) == {}


import asyncio
import pytest
from test_integration import start, stop, wait_for


@pytest.mark.asyncio
async def test_job_live_lifecycle(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        assert await wait_for(lambda: ctrl.last_snap is not None)
        ctrl.resume()
        ctrl.chg_job = None
        names = [u["name"] for u in ctrl.cfg["units"]]
        job, err = await ctrl.charge_start({"target": 60, "units": [names[1]], "power_w": 500}, "Test")
        assert job and not err
        assert await wait_for(lambda: any(c[:2] == ("select", "select_option") and c[2].get("option") == "charge" for c in m.calls)
                              or any(c[:2] == ("number", "set_value") and c[2]["entity_id"] == "number.pwr_b" for c in m.calls))
        assert ctrl.status["charge"]["active"]
        # Ziel erreicht -> Auftrag endet von selbst
        m.set_state("sensor.soc_b", 61)
        assert await wait_for(lambda: ctrl.chg_job is None)
        assert ctrl.chg_last["kind"] == "done"
        # neuer Auftrag, dann Stopp
        await ctrl.charge_start({"target": 90}, "Test")
        assert ctrl.chg_job
        await ctrl.kill("Test")
        assert ctrl.chg_job is None and ctrl.chg_last["kind"] == "stopped"
        assert not (await ctrl.charge_start({"target": 90}))[0]       # gestoppt: kein Start
        ctrl.resume()
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_job_persist_and_api(tmp_path):
    import main as appmain
    from aiohttp.test_utils import TestClient, TestServer
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        assert await wait_for(lambda: ctrl.last_snap is not None)
        ctrl.resume()
        async with TestClient(TestServer(appmain.build_app(ctrl, ctrl.store, ha))) as c:
            r = await (await c.post("/api/charge/estimate", json={"target": 90})).json()
            assert r["estimate"]["kwh"] > 0
            bad = await c.post("/api/charge/start", json={"target": "x"})
            assert bad.status == 400
            ok = await (await c.post("/api/charge/start", json={"target": 90})).json()
            assert ok["ok"] and ok["active"]
            assert (await (await c.get("/api/charge")).json())["job"]["target"] == 90
            import charge as ch
            from util import load_json
            assert load_json(ctrl.chg_path, {})["job"]["target"] == 90
            assert (await (await c.post("/api/charge/stop")).json())["changed"]
            assert (await (await c.get("/api/charge")).json())["active"] is False
    finally:
        await stop(m, tasks)


def test_automation_charge_rule():
    import automation
    r = automation.clean_rules([{"name": "x", "when": {"kind": "time", "at": "02:00"},
                                "then": {"kind": "charge", "target": 150, "power_w": "300", "units": ["A", 4]}}])
    assert r[0]["then"] == {"kind": "charge", "target": 100, "power_w": 300, "units": ["A"]}
    assert "100 %" in automation.describe(r[0])


# ---- Entladesperre ----
def test_sperre_verhindert_entladen_laesst_pv_durch():
    cfg = mk_cfg()
    units = [mk_unit(cfg, i, 80) for i in range(2)]
    units[0]["dis_lock"] = True
    units[0]["pv"] = 300
    decide(cfg, mk_snap(cfg, 600, units))
    assert units[0]["p"] <= 290 and units[0]["dcap"] == units[0]["pvcap"]
    assert units[1]["p"] > 0                     # der andere gibt ab


def test_sperre_ohne_pv_gibt_nichts_ab():
    cfg = mk_cfg()
    units = [mk_unit(cfg, 0, 80)]
    units[0]["dis_lock"] = True
    decide(cfg, mk_snap(cfg, 600, units))
    assert units[0]["p"] == 0


def test_job_sperrt_entladen_waehrend_laden():
    cfg = mk_cfg()
    units = [mk_unit(cfg, 0, 10), mk_unit(cfg, 1, 80)]
    decide(cfg, mk_snap(cfg, 600, units, charge=job(units=["U0"])))
    assert units[0]["p"] < 0 and units[1]["p"] == 0
    units = [mk_unit(cfg, 0, 10), mk_unit(cfg, 1, 80)]
    decide(cfg, mk_snap(cfg, 600, units, charge=job(units=["U0"], nodis=False)))
    assert units[1]["p"] > 0


def test_hold_bereinigt():
    assert charge.clean_job({"target": 50, "hold": {"mode": "until", "at": "08:00"}})["hold"] == {"mode": "until", "at": "08:00"}
    assert charge.clean_job({"target": 50, "hold": {"mode": "until", "at": "99:00"}})["hold"]["mode"] == "manual"
    assert charge.clean_job({"target": 50})["hold"]["mode"] == "none"


@pytest.mark.asyncio
async def test_sperre_api_ablauf_und_halten(tmp_path):
    import main as appmain
    from aiohttp.test_utils import TestClient, TestServer
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        assert await wait_for(lambda: ctrl.last_snap is not None)
        ctrl.resume(); ctrl.chg_job = None; ctrl.locks.clear()
        names = [u["name"] for u in ctrl.cfg["units"]]
        async with TestClient(TestServer(appmain.build_app(ctrl, ctrl.store, ha))) as c:
            assert (await c.post("/api/locks", json={"unit": "gibtsnicht", "on": True})).status == 400
            r = await (await c.post("/api/locks", json={"unit": names[0], "on": True})).json()
            assert names[0] in r["locks"]
            assert await wait_for(lambda: ctrl.status.get("locks") and names[0] in ctrl.status["locks"])
            assert await wait_for(lambda: any(u["dis_lock"] for u in ctrl.status["units"]))
            ctrl.locks[names[0]]["until"] = 1.0                 # abgelaufen
            assert await wait_for(lambda: names[0] not in ctrl.locks)
            # Ziel erreicht + halten bis Uhrzeit
            await ctrl.charge_start({"target": 60, "units": [names[1]], "hold": {"mode": "manual"}}, "Test")
            m.set_state("sensor.soc_b", 61)
            assert await wait_for(lambda: ctrl.chg_job is None)
            assert names[1] in ctrl.locks and ctrl.locks[names[1]]["until"] == 0
            r = await (await c.post("/api/locks", json={"unit": names[1], "on": False})).json()
            assert names[1] not in r["locks"]
    finally:
        ctrl.locks.clear()
        await stop(m, tasks)
