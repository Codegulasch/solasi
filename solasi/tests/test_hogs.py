import os, sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import hogs as H
from util import now_local


def mk(tmp_path):
    return H.Hogs(str(tmp_path / "h.db"))


def feed(h, day_start, minutes, vals, step=10):
    """vals: {dev: fn(minute_of_day)->W}; schreibt Messwerte im 10-s-Takt."""
    t = int(day_start.timestamp())
    for m in range(minutes):
        for s in range(0, 60, step):
            h.sample({d: f(m) for d, f in vals.items()}, ts=t + m * 60 + s)
    h.flush()


def today0():
    return now_local().replace(hour=0, minute=0, second=0, microsecond=0)


def test_clean_hogs():
    c = H.clean_hogs({"devices": [{"name": "Kühlschrank", "power": "sensor.a"}, {"name": "Kühlschrank", "power": "sensor.b", "phase": "L2"},
                                  {"name": "x", "power": ""}, "müll", {"name": "_house", "power": "sensor.c", "id": "_house"}]})
    ids = [d["id"] for d in c["devices"]]
    assert len(ids) == 3 and len(set(ids)) == 3 and "_house" not in ids
    assert c["devices"][1]["phase"] == "L2" and c["devices"][0]["phase"] == ""
    assert H.clean_hogs(None) == {"devices": []}


def test_watts_units():
    assert H._watts("1.5", "kW") == 1500.0 and H._watts("20", "W") == 20.0
    assert H._watts("unavailable", "W") is None and H._watts("nan", "W") is None


def test_rank_share_rest_and_standby(tmp_path):
    h = mk(tmp_path)
    d0 = today0()
    # 60 Minuten: Gerät a konstant 100 W, b konstant 10 W (Standby), Haus 300 W
    feed(h, d0 + timedelta(hours=1), 60, {"a": lambda m: 100, "b": lambda m: 10, H.HOUSE: lambda m: 300})
    devs = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
    r = h.rank(devs, days=1, price_ct=30.0)
    assert [x["id"] for x in r["devices"]] == ["a", "b"]
    assert abs(r["devices"][0]["kwh"] - 0.1) < 1e-6 and abs(r["house_kwh"] - 0.3) < 1e-6
    assert abs(r["devices"][0]["share"] - 33.3) < 0.1
    assert abs(r["rest_kwh"] - 0.19) < 1e-6 and abs(r["rest_share"] - 63.3) < 0.1
    assert r["devices"][1]["standby_w"] == 10
    # Hochrechnung: 100 W über 60 Minuten -> kWh/Jahr = 0.1 * 365*24
    assert abs(r["devices"][0]["kwh_year"] - 0.1 * 365 * 24) < 1


def test_time_of_day_filter_and_wrap(tmp_path):
    h = mk(tmp_path)
    d0 = today0()
    feed(h, d0, 24 * 60, {"a": lambda m: 200 if m < 360 else 0, H.HOUSE: lambda m: 400}, step=30)
    devs = [{"id": "a", "name": "A"}]
    night = h.rank(devs, 1, 0, 360)["devices"][0]["kwh"]
    day = h.rank(devs, 1, 360, 1440)["devices"][0]["kwh"]
    assert abs(night - 1.2) < 1e-6 and day == 0
    wrap = h.rank(devs, 1, 22 * 60, 6 * 60)["devices"][0]["kwh"]      # 22–6 Uhr: nur 0–6 Uhr trägt bei
    assert abs(wrap - 1.2) < 1e-6
    # Wochentage: nur ein anderer Wochentag -> nichts
    other = [(d0.weekday() + 1) % 7]
    assert h.rank(devs, 1, None, None, other)["devices"][0]["kwh"] == 0


def test_curve_resolutions_and_compare(tmp_path):
    h = mk(tmp_path)
    d0 = today0()
    feed(h, d0, 120, {"a": lambda m: 50 + m}, step=10)
    day = d0.strftime("%Y-%m-%d")
    c10 = h.curve("a", day, 10)
    c1 = h.curve("a", day, 60)
    c15 = h.curve("a", day, 900)
    assert len(c10) == 720 and len(c1) == 120 and len(c15) == 8
    assert c15[0]["t"] == 0 and c15[1]["t"] == 900 and abs(c15[0]["w"] - 57) < 0.6
    assert h.curve("a", (d0 - timedelta(days=1)).strftime("%Y-%m-%d"), 60) == []


def test_profile_and_cleanup_and_remove(tmp_path):
    h = mk(tmp_path)
    d0 = today0()
    feed(h, d0 + timedelta(hours=5), 120, {"a": lambda m: 80})
    p = h.profile("a", 1)
    assert p[5] == 80 and p[6] == 80 and p[7] is None and p[0] is None
    h.remove_device("a")
    assert h.rank([{"id": "a", "name": "A"}], 1)["devices"][0]["kwh"] == 0
    # Aufräumen: alte Rohdaten verschwinden
    h.sample({"x": 5}, ts=int(d0.timestamp()) - 10 * 86400)
    h.cleanup()
    assert h.db.execute("SELECT COUNT(*) FROM raw WHERE dev='x'").fetchone()[0] == 0


def test_none_values_skipped(tmp_path):
    h = mk(tmp_path)
    h.sample({"a": None, H.HOUSE: 100}, ts=int(today0().timestamp()) + 5)
    h.flush()
    assert h.db.execute("SELECT COUNT(*) FROM minute WHERE dev='a'").fetchone()[0] == 0


import asyncio, tempfile
import pytest
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_api_hogs_end_to_end(tmp_path, monkeypatch):
    import main as appmain
    from controller import Controller, ConfigStore
    from ha import HA
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    ctrl.hogs = H.Hogs(str(tmp_path / "h.db"))
    ha.states = {"sensor.plug_power": {"entity_id": "sensor.plug_power", "state": "120",
                                      "attributes": {"friendly_name": "Plug Power", "unit_of_measurement": "W", "device_class": "power"}},
                 "sensor.kw": {"entity_id": "sensor.kw", "state": "1.5", "attributes": {"unit_of_measurement": "kW"}},
                 "sensor.temp": {"entity_id": "sensor.temp", "state": "20", "attributes": {"unit_of_measurement": "°C"}}}
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        d = await (await c.get("/api/hogs/discover")).json()
        assert [s["entity"] for s in d["sensors"]] == ["sensor.plug_power", "sensor.kw"]
        cfg = await (await c.get("/api/config")).json()
        cfg["hogs"] = {"devices": [{"name": "Plug", "power": "sensor.plug_power", "icon": "🔌"}, {"name": "Heizer", "power": "sensor.kw"}]}
        assert (await (await c.post("/api/config", json=cfg)).json())["ok"]
        ctrl.status = {"house_w": 900}
        ctrl.hogs_sample()
        ctrl.hogs.flush()
        r = await (await c.get("/api/hogs?days=1")).json()
        assert r["configured"] == 2
        by = {x["id"]: x for x in r["devices"]}
        assert "plug" in by and "heizer" in by
        assert r["house_kwh"] >= 0
        cv = await (await c.get("/api/hogs/curve?dev=plug&res=10")).json()
        assert cv["points"] and cv["points"][0]["w"] == 120
        cv = await (await c.get("/api/hogs/curve?dev=heizer&res=10")).json()
        assert cv["points"][0]["w"] == 1500            # kW wurde in W umgerechnet
        assert (await c.get("/api/hogs/curve?dev=fremd")).status == 400
        assert (await c.get("/api/hogs/curve?dev=plug&day=quatsch")).status == 400
        # Gerät entfernen löscht seine Daten
        cfg["hogs"] = {"devices": [cfg["hogs"]["devices"][1]]}
        await c.post("/api/config", json=cfg)
        assert ctrl.hogs.curve("plug", None, 10) == []
