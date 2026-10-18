import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import phases as P


def cfg(**kw):
    return P.clean_phases({"enabled": True, "sensors": {"L1": {"power": "sensor.p1"}, "L2": {"power": "sensor.p2"}, "L3": {"power": "sensor.p3"}}, **kw})


class FakeHA:
    def __init__(self, st, units=None):
        self.st, self.u = st, units or {}

    def state(self, e):
        return self.st.get(e)

    def attr(self, e, k, d=None):
        return self.u.get(e, d)


def test_clean():
    c = P.clean_phases({"fuse_a": "99999", "warn_pct": 5, "feed": "L9", "sensors": {"L1": {"power": " sensor.x "}}})
    assert c["fuse_a"] == 125 and c["warn_pct"] == 50 and c["feed"] == {} and c["sensors"]["L1"]["power"] == "sensor.x" and c["sensors"]["L3"]["power"] == ""
    assert P.clean_phases(None)["enabled"] is False
    assert P.clean_phases({"feed": "L2"})["feed"] == {"*": "L2"}
    assert P.clean_phases({"feed": {"HÜTTE": "L1", "x": "L9"}})["feed"] == {"HÜTTE": "L1"}


def test_read_and_invert_and_kw():
    ha = FakeHA({"sensor.p1": "1.2", "sensor.p2": "300", "sensor.p3": "unavailable"}, {"sensor.p1": "kW"})
    v = P.read(cfg(), ha)
    assert v["L1"]["w"] == 1200 and v["L2"]["w"] == 300 and v["L3"]["w"] is None
    assert P.read(cfg(invert=True), ha)["L2"]["w"] == -300


def test_imbalance_and_fuse():
    c = cfg(fuse_a=16, warn_pct=80)
    vals = {"L1": {"w": 3000, "v": 230, "a": 13.0}, "L2": {"w": 500, "v": 230, "a": None}, "L3": {"w": -200, "v": None, "a": None}}
    r = P.analyse(c, vals)
    assert r["imbalance_w"] == 3200 and r["max_phase"] == "L1"
    assert r["fuse"]["phase"] == "L1" and r["fuse"]["pct"] == 81 and r["fuse"]["warn"] is True
    assert P.analyse(cfg(), vals)["fuse"] is None          # ohne Sicherung keine Auslastung


def simulate(feed_of, steps=60, noise=60, seed=1, together=False):
    """feed_of: {Speicher: Phase}. Die Speicher ändern ihre Leistung unabhängig (oder gemeinsam)."""
    rnd = random.Random(seed)
    det = P.FeedDetector()
    base = {"L1": 400.0, "L2": 250.0, "L3": 600.0}
    t = 1000.0
    for i in range(steps):
        outs = {}
        shared = rnd.choice([0, 100, 200, 300, 450, 600, 800])
        for u in feed_of:
            outs[u] = shared if together else rnd.choice([0, 100, 200, 300, 450, 600, 800])
        for p in base:
            base[p] += rnd.uniform(-noise, noise)
        vals = dict(base)
        for u, ph in feed_of.items():
            vals[ph] -= outs[u]
        det.update(t, outs, vals)
        t += 10
    return det


def test_detects_each_phase():
    for feed in ("L1", "L2", "L3"):
        r = simulate({"A": feed}).result()["units"]["A"]
        assert r["phase"] == feed, (feed, r)
        assert r["confidence"] >= 60


def test_two_units_on_different_phases():
    for fa, fb in (("L1", "L2"), ("L3", "L1"), ("L2", "L3")):
        r = simulate({"HÜTTE": fa, "DACH": fb}, steps=80).result()["units"]
        assert r["HÜTTE"]["phase"] == fa and r["DACH"]["phase"] == fb, (fa, fb, r)


def test_two_units_same_phase_and_lockstep_is_not_guessed():
    r = simulate({"A": "L2", "B": "L2"}, steps=80).result()["units"]
    assert r["A"]["phase"] == "L2" and r["B"]["phase"] == "L2"
    # Ändern sich beide immer gleichzeitig und auf verschiedenen Phasen, ist die Zuordnung nicht eindeutig
    r = simulate({"A": "L1", "B": "L3"}, steps=80, together=True).result()["units"]
    assert not (r["A"]["phase"] == "L1" and r["B"]["phase"] == "L3" and r["A"]["confidence"] > 80 and r["B"]["confidence"] > 80)


def test_unknown_without_data_and_with_flat_output():
    det = P.FeedDetector()
    assert det.result()["units"] == {}
    for i in range(30):                                  # Leistung bleibt gleich -> nichts zu lernen
        det.update(1000 + i * 10, {"A": 300}, {"L1": 100, "L2": 100, "L3": 100})
    assert all(v["phase"] == "" for v in det.result()["units"].values())


def test_gaps_and_missing_values_are_ignored():
    det = P.FeedDetector()
    det.update(0, {"A": 0}, {"L1": 0, "L2": 0, "L3": 0})
    det.update(500, {"A": 800}, {"L1": -800, "L2": 0, "L3": 0})     # zu große Lücke
    det.update(510, {"A": 0}, {"L1": None, "L2": 0, "L3": 0})        # fehlender Wert
    assert det.n == 0


def test_persist_and_reset(tmp_path):
    p = str(tmp_path / "ph.json")
    det = P.FeedDetector(p)
    rnd = random.Random(3); t = 0
    for i in range(30):
        out = rnd.choice([0, 300, 600]); det.update(t, {"A": out}, {"L1": 100, "L2": 100 - out, "L3": 100}); t += 10
    det.save()
    again = P.FeedDetector(p)
    assert again.result()["units"]["A"]["phase"] == "L2"
    again.reset()
    assert P.FeedDetector(p).result()["units"] == {}


def test_discover_guesses_phase():
    st = {"sensor.shellyem3_phase_a_power": {"state": "10", "attributes": {"unit_of_measurement": "W", "device_class": "power", "friendly_name": "Shelly 3EM Phase A Power"}},
          "sensor.shellyem3_phase_b_voltage": {"state": "231", "attributes": {"unit_of_measurement": "V", "friendly_name": "Shelly 3EM Phase B Voltage"}},
          "sensor.shellyem3_total_power": {"state": "40", "attributes": {"unit_of_measurement": "W", "friendly_name": "Shelly 3EM Total Power"}},
          "sensor.temp": {"state": "20", "attributes": {"unit_of_measurement": "°C"}}}
    d = {x["entity"]: x for x in P.discover(st)}
    assert d["sensor.shellyem3_phase_a_power"]["phase"] == "L1" and d["sensor.shellyem3_phase_a_power"]["kind"] == "power"
    assert d["sensor.shellyem3_phase_b_voltage"]["phase"] == "L2" and d["sensor.shellyem3_phase_b_voltage"]["kind"] == "voltage"
    assert d["sensor.shellyem3_total_power"]["phase"] == "" and "sensor.temp" not in d
    st2 = {"sensor.s3em_phase_c_active_power": {"state": "1", "attributes": {"unit_of_measurement": "W", "friendly_name": "Zähler Phase C Active power"}},
           "sensor.em_channel_c_power": {"state": "1", "attributes": {"unit_of_measurement": "W", "friendly_name": "EM Channel C Power"}},
           "sensor.x_l3_current": {"state": "1", "attributes": {"unit_of_measurement": "A", "friendly_name": "Grid L3 current"}},
           "sensor.em_kanal_2_leistung": {"state": "1", "attributes": {"unit_of_measurement": "W", "friendly_name": "EM Kanal 2 Leistung"}}}
    d2 = {x["entity"]: x["phase"] for x in P.discover(st2)}
    assert d2 == {"sensor.s3em_phase_c_active_power": "L3", "sensor.em_channel_c_power": "L3", "sensor.x_l3_current": "L3", "sensor.em_kanal_2_leistung": "L2"}


import asyncio, tempfile
import pytest
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_controller_and_api(tmp_path, monkeypatch):
    import main as appmain
    from controller import Controller, ConfigStore
    from ha import HA
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    ctrl.feed_det = P.FeedDetector(str(tmp_path / "ph.json"))
    ha.states = {f"sensor.p{i}": {"entity_id": f"sensor.p{i}", "state": "100", "attributes": {"unit_of_measurement": "W", "friendly_name": f"Phase {'ABC'[i-1]} Power"}} for i in (1, 2, 3)}
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        cfgj = await (await c.get("/api/config")).json()
        assert cfgj["phases"]["enabled"] is False
        cfgj["phases"] = {"enabled": True, "fuse_a": 16, "sensors": {f"L{i}": {"power": f"sensor.p{i}"} for i in (1, 2, 3)}}
        assert (await (await c.post("/api/config", json=cfgj)).json())["ok"]
        # Speicher-Ausgang springt, nur L2 folgt gegenläufig
        import time as _t
        t0 = _t.time(); out = 0; clock = {"t": t0}
        import controller as ctl
        monkeypatch.setattr(ctl.time, "time", lambda: clock["t"])
        for i in range(16):
            out = [0, 300, 600, 150][i % 4] + i * 0
            ha.states["sensor.p2"]["state"] = str(100 - out)
            clock["t"] = t0 + i * 10
            ctrl.phases_cycle({"out_w": out, "has_out": True, "units": [{"k": "A", "ac": out}]})
        v = (await (await c.get("/api/phases")).json())["view"]
        assert v["enabled"] and v["feed_units"][0]["detected"] == "L2" and v["feed_units"][0]["name"] == "A" and v["phases"]["L1"]["w"] == 100
        assert v["fuse"]["phase"] in ("L1", "L2", "L3")
        r = await (await c.post("/api/phases/reset")).json()
        assert r["ok"] and ctrl.feed_det.result()["units"] == {}
        d = await (await c.get("/api/phases/discover")).json()
        assert [s["phase"] for s in d["sensors"]] == ["L1", "L2", "L3"]
