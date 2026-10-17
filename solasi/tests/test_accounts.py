import os, sys, tempfile, json
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["SOLASI_ALLOW_ALL"] = ""
from aiohttp.test_utils import TestClient, TestServer
import accounts as A
import main as appmain
from controller import Controller, ConfigStore
from ha import HA


class Clock:
    t = 1000.0
    def __call__(self): return self.t


def mk(tmp_path):
    clk = Clock()
    return A.AccountStore(str(tmp_path / "a.json"), clock=clk), clk


def test_konten_passwort_sicher_gespeichert(tmp_path):
    s, _ = mk(tmp_path)
    assert s.create("Stefan", "geheim123", "owner") is None
    raw = open(tmp_path / "a.json").read()
    assert "geheim123" not in raw and json.loads(raw)["users"]["Stefan"]["hash"]
    assert "mindestens" in s.create("Anna", "kurz", "member") and "schon" in s.create("stefan", "geheim123", "member")
    assert s.create("Anna", "langgenug1", "chef") == "Unbekannte Rolle" and s.create("A", "langgenug1", "member")
    tok, err = s.login("stefan", "geheim123")           # Name unabhängig von Groß/Klein
    assert tok and s.user_for(tok) == {"name": "Stefan", "role": "owner"}
    s2 = A.AccountStore(str(tmp_path / "a.json"))        # persistent
    assert s2.has_any() and s2.login("Stefan", "geheim123")[0]


def test_sperre_nach_fehlversuchen(tmp_path):
    s, clk = mk(tmp_path)
    s.create("Stefan", "geheim123", "owner")
    for _ in range(A.MAX_FAILS):
        assert s.login("Stefan", "falsch", "1.2.3.4")[0] is None
    tok, err = s.login("Stefan", "geheim123", "1.2.3.4")
    assert tok is None and "Zu viele" in err                    # auch das richtige Passwort wird gesperrt
    assert s.login("Stefan", "geheim123", "9.9.9.9")[0]         # andere Adresse nicht betroffen
    clk.t += A.LOCK_S + 1
    assert s.login("Stefan", "geheim123", "1.2.3.4")[0]


def test_rollen_regeln_und_schutz_letzter_besitzer(tmp_path):
    s, clk = mk(tmp_path)
    s.create("Stefan", "geheim123", "owner"); s.create("Anna", "langgenug1", "member")
    assert s.delete("Stefan") and s.set_role("Stefan", "viewer")        # letzter Besitzer bleibt
    tok = s.login("Anna", "langgenug1")[0]
    assert s.set_password("Anna", "neuespw123") is None and s.user_for(tok) is None   # Passwortwechsel beendet Sitzungen
    tok = s.login("Anna", "neuespw123")[0]
    clk.t += A.SESSION_S + 1
    assert s.user_for(tok) is None
    assert A.allowed("owner", "DELETE", "/api/accounts/x") and not A.allowed("member", "GET", "/api/accounts")
    assert A.allowed("member", "POST", "/api/goals/mode") and not A.allowed("member", "POST", "/api/config")
    assert A.allowed("viewer", "GET", "/api/status") and not A.allowed("viewer", "POST", "/api/goals/mode")


@pytest.mark.asyncio
async def test_direkter_port_verlangt_anmeldung(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    accts, _ = mk(tmp_path)
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha, accts, direct=True))) as c:
        r = await c.get("/")
        assert r.status == 200 and "SOLASI" in await r.text() and "Melde dich an" not in await r.text()   # ohne Konto: offen
        assert (await c.get("/api/config")).status == 200
        j = await (await c.get("/api/me")).json()
        assert j["open"] is True and j["role"] == "owner" and j["direct"] is True
        assert (await c.post("/api/config", json=await (await c.get("/api/config")).json())).status == 200
        accts.create("Stefan", "geheim123", "owner"); accts.create("Anna", "langgenug1", "member"); accts.create("Opa", "langgenug2", "viewer")
        assert (await c.get("/api/config")).status == 401                           # mit Konten: Anmeldung nötig
        assert "Melde dich an" in await (await c.get("/")).text()
        assert (await c.post("/api/login", json={"name": "Stefan", "password": "falsch"})).status == 401
        assert (await c.post("/api/login", json={"name": "Anna", "password": "langgenug1"})).status == 200
        assert (await c.get("/api/config")).status == 200
        assert (await c.get("/api/me")).status == 200
        j = await (await c.get("/api/me")).json()
        assert j["role"] == "member" and j["name"] == "Anna" and j["direct"] is True
        assert (await c.get("/api/accounts")).status == 403                         # Mitbewohner verwaltet keine Konten
        assert (await c.post("/api/config", json={})).status == 403
        r = await c.post("/api/goals/mode", json={"id": "emergency"})
        assert r.status == 200 and any("Anna" in e["msg"] for e in ctrl.events)     # Name aus dem Konto im Protokoll
        await c.post("/api/logout")
        assert (await c.get("/api/config")).status == 401
        await c.post("/api/login", json={"name": "Opa", "password": "langgenug2"})
        assert (await c.get("/api/status")).status == 200 and (await c.post("/api/goals/mode", json={"id": "balanced"})).status == 403
        await c.post("/api/logout")
        await c.post("/api/login", json={"name": "Stefan", "password": "geheim123"})
        r = await c.post("/api/accounts", json={"create": True, "name": "Neu", "password": "nochmal123", "role": "viewer"})
        assert (await r.json())["ok"] and len((await (await c.get("/api/accounts")).json())["users"]) == 4
        assert (await c.delete("/api/accounts/Stefan")).status == 400                # letzter Besitzer
        assert (await c.delete("/api/accounts/Neu")).status == 200


@pytest.mark.asyncio
async def test_ingress_verwaltet_konten_ohne_anmeldung(tmp_path):
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    accts, _ = mk(tmp_path)
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha, accts))) as c:
        assert (await c.get("/api/me")).status == 200
        assert (await (await c.get("/api/me")).json())["role"] == "owner"
        r = await c.post("/api/accounts", json={"create": True, "name": "Stefan", "password": "geheim123", "role": "owner"})
        assert (await r.json())["ok"]
        assert (await c.delete("/api/accounts/Stefan")).status == 400                # letzter Besitzer
        r = await c.post("/api/accounts", json={"name": "Stefan", "password": "kurz"})
        assert r.status == 400
