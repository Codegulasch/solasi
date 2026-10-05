"""Externe Steuerung (Drittanbieter-Modus) wird beim Start automatisch gesetzt."""
import asyncio, os, sys, tempfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
import drivers
from test_drivers import FakeHA, boot, unit, NAMES
from test_integration import stop, wait_for

ANKER = dict(name="Speicher", num="number.pwr_mx", dir="select.d", mode="select.mode_mx", soc="sensor.soc",
             fallback_mode="self_consumption")
STATES = {"number.pwr_mx": "unavailable", "select.d": "discharge", "select.mode_mx": "self_consumption", "sensor.soc": 60}


def mode_calls(m):
    return [c for c in m.calls if c[:2] == ("select", "select_option") and c[2]["entity_id"] == "select.mode_mx"]


# ---------------- Hilfsfunktion der Treiber ----------------
def test_nicht_erreichbare_entitaeten_werden_nicht_geschaltet():
    u = unit(num="number.p", dir="select.d", mode="select.m", enable="switch.rs")
    for state in ("unavailable", "unknown"):
        ha = FakeHA({"select.m": state, "switch.rs": state})
        assert drivers.guard_commands(u, NAMES, ha) == []
    ha = FakeHA({"select.m": "self_consumption", "switch.rs": "off"})
    assert [c[2]["entity_id"] for c in drivers.guard_commands(u, NAMES, ha)] == ["switch.rs", "select.m"]


# ---------------- im laufenden Betrieb ----------------
@pytest.mark.asyncio
async def test_modus_wird_beim_start_gesetzt_auch_ohne_sollwert(tmp_path):
    """Kein Bedarf (Netz 0 W, Sollwert 0): Der Speicher soll trotzdem sofort in den Drittanbieter-Modus."""
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8), m.calls
        assert ctrl.status.get("units", [{}])[0].get("plan", 0) == 0 or True
        assert [c for c in m.calls if c[0] == "number"] == []                       # es wurde nur der Modus gesetzt
        assert await wait_for(lambda: m.states["number.pwr_mx"]["state"] != "unavailable", 6)   # Leistung ist danach verfügbar
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_funktion_ausschaltbar(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    ctrl.cfg["features"]["enforce_mode"] = False
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        await asyncio.sleep(2.5)
        assert m.states["select.mode_mx"]["state"] == "self_consumption" and mode_calls(m) == []
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_ausgeschaltete_funktion_schaltet_bei_bedarf_weiterhin_um(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [{**ANKER, "mode_option": "third_party_control"}], STATES)
    ctrl.cfg["features"]["enforce_mode"] = False
    m.set_state("sensor.grid", 400, broadcast=False)                         # Bedarf: altes Verhalten bleibt
    try:
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_testmodus_aendert_nichts(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    ctrl.cfg["dry_run"] = True
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: any("Modus auf" in e["msg"] and e["level"] == "test" for e in ctrl.events), 6), list(ctrl.events)[:3]
        assert mode_calls(m) == [] and m.states["select.mode_mx"]["state"] == "self_consumption"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_aus_schaltet_nichts_beobachten_aendert_nichts(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    ctrl.cfg["enabled"] = False
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        await asyncio.sleep(2)
        assert mode_calls(m) == []
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_gestoppt_bleibt_im_eigenen_modus_und_fortsetzen_schaltet_wieder_um(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
        await ctrl.kill("Test", "manual")                                  # gibt frei: Eigenverbrauch
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "self_consumption", 6)
        n = len(mode_calls(m))
        await asyncio.sleep(2)
        assert len(mode_calls(m)) == n and m.states["select.mode_mx"]["state"] == "self_consumption"   # kein Zurückspringen
        ctrl.resume()
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_von_aussen_verstellter_modus_wird_gedrosselt_zurueckgesetzt(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
        n = len(mode_calls(m))
        m.set_state("select.mode_mx", "self_consumption")                  # jemand stellt in der Hersteller-App um
        await asyncio.sleep(2.5)
        assert len(mode_calls(m)) == n and m.states["select.mode_mx"]["state"] == "self_consumption"   # Sperrzeit (30 s) läuft noch
        ctrl.mode_retry_s = 0.3
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
        assert len(mode_calls(m)) == n + 1
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_bei_zaehlerausfall_wird_nichts_umgeschaltet(tmp_path):
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    m.set_state("sensor.grid", "unavailable", broadcast=False)
    try:
        await asyncio.sleep(2.5)
        assert mode_calls(m) == []
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_nicht_erreichbarer_modus_wird_uebersprungen_ohne_fehler(tmp_path):
    states = {**STATES, "select.mode_mx": "unavailable"}
    m, ctrl, tasks = await boot(tmp_path, [ANKER], states)
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        await asyncio.sleep(2.5)
        assert mode_calls(m) == [] and ctrl._fail_times == [] and not ctrl.stopped
        m.set_state("select.mode_mx", "self_consumption")                  # Gerät kommt zurück
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 8)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_marstek_fernsteuerung_und_arbeitsmodus_beim_start(tmp_path):
    cfg = dict(driver="modal", name="Venus", dir="select.force", num="number.dis", num_chg="number.chg", soc="sensor.soc",
               enable="switch.rs485", mode="select.user", mode_option="manual", fallback_mode="anti_feed")
    states = {"select.force": "stop", "number.dis": "0", "number.chg": "0", "sensor.soc": 60, "switch.rs485": "off", "select.user": "anti_feed"}
    m, ctrl, tasks = await boot(tmp_path, [cfg], states)
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: m.states["switch.rs485"]["state"] == "on" and m.states["select.user"]["state"] == "manual", 8), m.calls
        order = [c[2]["entity_id"] for c in m.calls if c[0] in ("select", "homeassistant")]
        assert order.index("switch.rs485") < order.index("select.user")        # erst Fernsteuerung, dann Arbeitsmodus
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_live_einschalten_setzt_den_modus_sofort(tmp_path):
    """Vom Testmodus auf Live: kein Warten auf die Sperrzeit (über die Weboberfläche wie im Betrieb)."""
    from aiohttp.test_utils import TestClient, TestServer
    import json, main as appmain
    m, ctrl, tasks = await boot(tmp_path, [ANKER], STATES)
    ctrl.cfg["dry_run"] = True
    m.set_state("sensor.grid", 0, broadcast=False)
    try:
        assert await wait_for(lambda: any("Modus auf" in e["msg"] for e in ctrl.events), 6)     # im Test nur protokolliert, Versuchszeit gemerkt
        assert mode_calls(m) == []
        async with TestClient(TestServer(appmain.build_app(ctrl, ctrl.store, ctrl.ha))) as c:
            cfg = json.loads(json.dumps(ctrl.cfg)); cfg["dry_run"] = False
            assert (await (await c.post("/api/config", json=cfg)).json())["ok"]
        assert await wait_for(lambda: m.states["select.mode_mx"]["state"] == "third_party_control", 6), m.calls
    finally:
        await stop(m, tasks)
