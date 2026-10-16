import asyncio, os, sys, json
import pytest
import tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
os.environ["SOLASI_ALLOW_ALL"] = ""
from aiohttp.test_utils import TestClient, TestServer
import main as appmain
from controller import Controller, ConfigStore
from ha import HA


@pytest.mark.asyncio
async def test_api(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    ha.states = {"sensor.a": {"entity_id": "sensor.a", "state": "1", "attributes": {"friendly_name": "A"}},
                 "number.n": {"entity_id": "number.n", "state": "2", "attributes": {}}}
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        r = await c.get("/")
        assert r.status == 200 and "SOLASI" in await r.text()
        cfg = await (await c.get("/api/config")).json()
        assert cfg["enabled"] is False and cfg["dry_run"] is True and len(cfg["units"]) == 2 and len(cfg["surplus"]["slots"]) == 3
        cfg["grid"]["entity"] = "sensor.a"; cfg["enabled"] = True
        r = await c.post("/api/config", json=cfg)
        assert (await r.json())["ok"]
        assert json.load(open(tmp_path / "s.json"))["grid"]["entity"] == "sensor.a"   # persistiert
        ents = await (await c.get("/api/entities")).json()
        assert [e["id"] for e in ents] == ["number.n", "sensor.a"] and ents[1]["name"] == "A"
        st = await (await c.get("/api/status")).json()
        assert st["enabled"] is True and "events" in st
        r = await c.post("/api/config", data="kaputt", headers={"Content-Type": "application/json"})
        assert r.status == 400

def test_config_alt_ergaenzt(tmp_path):
    # alte/teilweise Konfiguration wird mit Standardwerten ergänzt
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"enabled": True, "units": [{"name": "X", "num": "number.x"}], "control": {"step": 5}}))
    st = ConfigStore(str(p))
    assert st.cfg["enabled"] is True and st.cfg["control"]["step"] == 5 and st.cfg["control"]["min_gap"] == 5
    assert st.cfg["units"][0]["num"] == "number.x" and st.cfg["units"][0]["max_dis"] == 800 and len(st.cfg["units"]) == 2

@pytest.mark.asyncio
async def test_zugriffsschutz(tmp_path):
    appmain.ALLOWED = {"172.30.32.2"}
    try:
        store = ConfigStore(str(tmp_path / "s.json"))
        ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
        async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
            r = await c.get("/api/config")
            assert r.status == 403          # nicht über den Supervisor-Proxy
    finally:
        appmain.ALLOWED = {"172.30.32.2", "127.0.0.1", "::1"}


def test_karte_wird_installiert(tmp_path):
    cfgdir = tmp_path / "ha"; cfgdir.mkdir(); (cfgdir / "configuration.yaml").write_text("")
    target, created = appmain.install_card([str(tmp_path / "nix"), str(cfgdir)])
    assert target == str(cfgdir / "www" / "solasi" / "solasi-card.js") and created is True
    assert "solasi-card" in open(target).read()
    # zweites Mal: www existiert bereits -> kein Neustart nötig
    target2, created2 = appmain.install_card([str(cfgdir)])
    assert target2 == target and created2 is False

def test_karte_ohne_config_ordner(tmp_path):
    assert appmain.install_card([str(tmp_path / "gibtsnicht")]) == (None, False)

@pytest.mark.asyncio
async def test_karte_endpunkte(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    ctrl.card.update(installed=True, target="/x", url="/local/solasi/solasi-card.js?v=1.2.0")
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        j = await (await c.get("/api/card")).json()
        assert j["installed"] is True and "custom:solasi-card" in j["yaml"]
        r = await c.get("/card.js")
        assert r.status == 200 and "javascript" in r.headers["Content-Type"] and "customElements.define" in await r.text()


def test_version_wird_in_die_karte_eingesetzt(tmp_path):
    assert "__VERSION__" not in appmain.card_text() and appmain.VERSION in appmain.card_text()
    cfgdir = tmp_path / "ha"; cfgdir.mkdir(); (cfgdir / "configuration.yaml").write_text("")
    target, _ = appmain.install_card([str(cfgdir)])
    text = open(target, encoding="utf-8").read()
    assert "__VERSION__" not in text and appmain.VERSION in text

def test_version_kommt_aus_config_yaml(monkeypatch):
    monkeypatch.delenv("SOLASI_VERSION", raising=False)
    v = appmain.read_version()
    assert v and v != "dev" and v[0].isdigit()
    monkeypatch.setenv("SOLASI_VERSION", "9.9.9")
    assert appmain.read_version() == "9.9.9"


@pytest.mark.asyncio
async def test_meter_history(tmp_path):
    store = ConfigStore(str(tmp_path / "m.json"))
    store.cfg["meters"]["items"] = [{"entity": "sensor.wasser", "name": "W"}]
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    ha.states = {"sensor.wasser": {"entity_id": "sensor.wasser", "state": "5", "attributes": {"friendly_name": "Wasser", "unit_of_measurement": "m³"}}}
    calls = []

    async def fake_call(payload, timeout=15):
        calls.append(payload["type"])
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).timestamp() * 1000
        return {"sensor.wasser": [{"start": now - 3600_000, "change": 0.25}]}
    ha.call = fake_call
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        r = await (await c.get("/api/meter_history?entity=sensor.wasser&days=7")).json()
        assert r["ok"] and r["unit"] == "m³" and len(r["days"]) == 7 and r["source"] == "statistik"
        assert any(d["value"] for d in r["days"]) and calls == ["recorder/statistics_during_period"]
        bad = await c.get("/api/meter_history?entity=sensor.fremd")
        assert bad.status == 400
