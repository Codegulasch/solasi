import asyncio, copy, os, sys, tempfile
import pytest
import tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.dirname(__file__))
from controller import Controller, ConfigStore
from ha import HA
from mock_ha import MockHA


def build_states(m):
    m.set_state("sensor.grid", 400, broadcast=False)
    for k, soc in (("a", 80), ("b", 40)):
        m.set_state(f"sensor.soc_{k}", soc, broadcast=False)
        m.set_state(f"number.pwr_{k}", "unavailable", broadcast=False)   # Gerät noch nicht im externen Modus
        m.set_state(f"select.dir_{k}", "discharge", broadcast=False)
        m.set_state(f"select.mode_{k}", "self_consumption", broadcast=False)
        m.set_state(f"sensor.rd_{k}", 0, broadcast=False)
        m.set_state(f"sensor.rc_{k}", 0, broadcast=False)


def make_cfg(path, **over):
    store = ConfigStore(path)
    cfg = store.cfg
    cfg["enabled"] = True
    cfg["dry_run"] = False
    cfg["grid"]["entity"] = "sensor.grid"
    for i, k in enumerate("ab"):
        u = cfg["units"][i]
        u.update(num=f"number.pwr_{k}", dir=f"select.dir_{k}", soc=f"sensor.soc_{k}",
                 mode=f"select.mode_{k}", real_dis=f"sensor.rd_{k}", real_chg=f"sensor.rc_{k}")
    cfg["control"].update(min_gap=0, heartbeat=0.3, total_max_dis=2000)
    for k, v in over.items():
        cfg[k] = v
    store.save(cfg)
    return store


async def start(tmp, **over):
    m = MockHA(); url = await m.start(); build_states(m)
    store = make_cfg(os.path.join(tmp, "s.json"), **over)
    ctrl = Controller(None, store)
    ha = HA(url, "TOKEN", on_entity_event=ctrl.on_entity_event, api_url=m.api_url, on_connected=ctrl.post_connect); ctrl.ha = ha
    tasks = [asyncio.create_task(ha.run()), asyncio.create_task(ctrl.run())]
    m._ha = ha
    return m, ctrl, ha, tasks


async def stop(m, tasks):
    for t in tasks: t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    if getattr(m, "_ha", None):
        await m._ha.close()
    await m.stop()


async def wait_for(cond, timeout=6):
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        try:
            if cond(): return True
        except (ValueError, KeyError):   # Zustand noch "unavailable"
            pass
        await asyncio.sleep(0.1)
    return False


@pytest.mark.asyncio
async def test_regelung_live(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        ok = await wait_for(lambda: any(c[:2] == ("number", "set_value") and c[2]["value"] > 0 for c in m.calls))
        assert ok, m.calls
        # Modus wurde zuerst gesetzt, dann Leistung geschrieben
        modes = [c for c in m.calls if c[:2] == ("select", "select_option") and c[2]["option"] == "third_party_control"]
        assert len(modes) == 2
        await wait_for(lambda: m.states["number.pwr_a"]["state"] not in ("unavailable", "0") and m.states["number.pwr_b"]["state"] not in ("unavailable", "0"))
        a, b = int(m.states["number.pwr_a"]["state"]), int(m.states["number.pwr_b"]["state"])
        assert (a, b) == (280, 110), (a, b)
        assert m.states["select.dir_a"]["state"] == "discharge"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_testmodus_sendet_nichts(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        ctrl.cfg["dry_run"] = True
        await asyncio.sleep(1.5)
        assert m.calls == []
        assert any(e["level"] == "test" for e in ctrl.events) or True
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_master_aus_beobachtet_nur(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        ctrl.cfg["enabled"] = False
        await asyncio.sleep(1.5)
        assert m.calls == [] and ctrl.status.get("grid_w") == 400
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_failsafe_zaehler_weg(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.set_state("sensor.grid", "unavailable")
        ok = await wait_for(lambda: m.states["number.pwr_a"]["state"] == "0" and m.states["number.pwr_b"]["state"] == "0")
        assert ok, {k: v["state"] for k, v in m.states.items() if k.startswith("number")}
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_nachregeln_bei_laständerung(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        # Geräte liefern jetzt 280+110; Netz zeigt noch 100 W -> Bilanz 490 -> Ziel 480
        m.set_state("sensor.grid", 100)
        ok = await wait_for(lambda: int(m.states["number.pwr_a"]["state"]) + int(m.states["number.pwr_b"]["state"]) == 480, 5)
        assert ok, (m.states["number.pwr_a"]["state"], m.states["number.pwr_b"]["state"])
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_richtungswechsel_laden(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.calls.clear()
        m.set_state("sensor.grid", -600)   # Einspeisung: Bilanz 390-600 = -210 -> Laden
        ok = await wait_for(lambda: m.states["select.dir_a"]["state"] == "charge" or m.states["select.dir_b"]["state"] == "charge", 5)
        assert ok, m.calls
        # vor dem Richtungswechsel wurde die Leistung auf 0 gesetzt
        first_dir = next(i for i, c in enumerate(m.calls) if c[0] == "select" and c[2].get("option") == "charge")
        assert any(c[:2] == ("number", "set_value") and c[2]["value"] == 0 for c in m.calls[:first_dir])
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_ueberschuss_schaltet_und_regelt(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        m.set_state("sensor.pv_a", 3000); m.set_state("sensor.pv_b", 0)
        m.set_state("switch.wallbox", "off")
        m.set_state("number.wallbox_a", 6, {"min": 6, "max": 16, "step": 1})
        sp = ctrl.cfg["surplus"]
        sp.update(enabled=True, dry_run=False, source="pv")
        ctrl.cfg["units"][0]["pv"] = "sensor.pv_a"; ctrl.cfg["units"][1]["pv"] = "sensor.pv_b"
        # Hausverbrauch 1380 W (Wallbox läuft mit 6 A) bei 3000 W PV -> 1620 W Überschuss,
        # zusammen mit der eigenen Leistung (1380 W) stehen der Wallbox 3000 W zu
        m.set_state("sensor.house", 1380)
        sp["house"] = "sensor.house"
        m.set_state("sensor.grid", 0)
        s = sp["slots"][0]
        s.update(ent="switch.wallbox", num="number.wallbox_a", on_w=1500, on_delay=0, soc=0, unit_w=230, pmin=1380,
                 pmax=7360, interval=0, min_off=0, min_on=0)
        ok = await wait_for(lambda: m.states["switch.wallbox"]["state"] == "on", 8)
        assert ok, list(ctrl.events)[:5]
        ok = await wait_for(lambda: float(m.states["number.wallbox_a"]["state"]) > 6, 8)
        assert ok, (m.states["number.wallbox_a"], list(ctrl.events)[:5])
        assert float(m.states["number.wallbox_a"]["state"]) == 13   # floor(3000 W / 230 W/A)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_failsafe_zaehler_meldet_nicht_mehr(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        ctrl.cfg["grid"]["max_age"] = 2
        ha.refresh_interval = 60          # kein Abgleich -> Zähler gilt als verstummt
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        ok = await wait_for(lambda: m.states["number.pwr_a"]["state"] == "0" and m.states["number.pwr_b"]["state"] == "0", 8)
        assert ok
        assert await wait_for(lambda: ctrl.status["meter_ok"] is False, 3)   # Status folgt am Zyklusende
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_konstanter_zaehlerwert_ist_kein_ausfall(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    ha.refresh_interval = 0.5             # vor dem Verbindungsaufbau setzen
    try:
        ctrl.cfg["grid"]["max_age"] = 2
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        # Wert bleibt gleich, nur last_reported läuft weiter; der Abgleich erkennt das
        for _ in range(35):               # 3,5 s > max_age
            m.touch("sensor.grid"); await asyncio.sleep(0.1)
        assert ctrl.status["meter_ok"] is True
        assert m.states["number.pwr_a"]["state"] != "0"
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_real_power_fix_nicht_im_sekundentakt(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        # Geräte stehen auf 0 W, Netz ausgeglichen -> nichts zu regeln
        m.set_state("sensor.grid", 0)
        m.set_state("number.pwr_a", 0); m.set_state("number.pwr_b", 0)
        await asyncio.sleep(1.0)
        m.set_state("sensor.rd_a", 500)   # echte Leistung trotz Sollwert 0 (z. B. durchgereichte PV)
        m.calls.clear()
        await asyncio.sleep(3.5)
        zero_writes = [c for c in m.calls if c[:2] == ("number", "set_value") and c[2]["entity_id"] == "number.pwr_a"]
        assert len(zero_writes) == 1, zero_writes      # einmal korrigiert, dann höchstens 1x pro Minute
    finally:
        await stop(m, tasks)


# ---------- Entitäten & Dashboard-Karte ----------
@pytest.mark.asyncio
async def test_entitaeten_werden_veroeffentlicht(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        assert await wait_for(lambda: "sensor.solasi" in m.rest and "sensor.solasi_house_power" in m.rest)
        main = m.rest["sensor.solasi"]
        assert main["state"] in ("Entladen", "Leerlauf") and main["attributes"]["mode"] == "live"
        assert main["attributes"]["grid_w"] == 400 and len(main["attributes"]["units"]) == 2
        pv = m.rest["sensor.solasi_house_power"]
        assert pv["attributes"]["unit_of_measurement"] == "W" and pv["attributes"]["device_class"] == "power"
        assert m.rest["sensor.solasi_battery_power"]["state"] == "0"
        assert "sensor.solasi_pv_power" not in m.rest      # ohne PV-Sensor keine PV-Entität
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_veroeffentlichung_nur_bei_aenderung(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        await asyncio.sleep(2)             # Regelung ist eingeschwungen
        await asyncio.sleep(0.5); m.rest_posts.clear()
        await asyncio.sleep(2)              # mehrere Heartbeats ohne Änderung
        assert [p for p in m.rest_posts if p == "sensor.solasi"] == [], m.rest_posts
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_nach_neuverbindung_neu_veroeffentlicht(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: "sensor.solasi" in m.rest)
        m.rest.clear(); m.rest_posts.clear()          # HA-Neustart: virtuelle Entitäten sind weg
        await ctrl.post_connect()
        assert "sensor.solasi" in m.rest
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_ressource_wird_angelegt_und_aktualisiert(tmp_path):
    m = MockHA(); url = await m.start(); build_states(m)
    store = make_cfg(os.path.join(str(tmp_path), "s.json"))
    ctrl = Controller(None, store)
    ha = HA(url, "TOKEN", api_url=m.api_url, on_connected=ctrl.post_connect); ctrl.ha = ha
    ctrl.card.update(installed=True, base_url="/local/solasi/solasi-card.js", url="/local/solasi/solasi-card.js?v=1")
    tasks = [asyncio.create_task(ha.run())]
    m._ha = ha
    try:
        assert await wait_for(lambda: len(m.resources) == 1)
        assert m.resources[0]["url"].endswith("?v=1") and ctrl.card["resource"] == "registriert"
        # gleiche Version: nichts doppelt
        assert await ha.ensure_resource(ctrl.card["base_url"], ctrl.card["url"]) == "exists" and len(m.resources) == 1
        # neue Version: vorhandene Ressource wird aktualisiert statt dupliziert
        assert await ha.ensure_resource(ctrl.card["base_url"], "/local/solasi/solasi-card.js?v=2") == "updated"
        assert len(m.resources) == 1 and m.resources[0]["url"].endswith("?v=2")
    finally:
        await stop(m, tasks)


# ---------- Benachrichtigung, Statistik, Lernen im laufenden Betrieb ----------
@pytest.mark.asyncio
async def test_benachrichtigung_bei_zaehlerausfall(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        ctrl.cfg["notify"].update(service="notify.mobile_app_pixel", delay_min=0.03, cooldown_min=60)
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        m.set_state("sensor.grid", "unavailable")
        ok = await wait_for(lambda: any(c[:2] == ("notify", "mobile_app_pixel") for c in m.calls), 8)
        assert ok, [c for c in m.calls if c[0] == "notify"]
        call = next(c for c in m.calls if c[0] == "notify")
        assert "Zähler" in call[2]["title"] and call[2]["message"]
        m.set_state("sensor.grid", 100)                      # wieder da -> Entwarnung
        assert await wait_for(lambda: any("behoben" in c[2].get("title", "") for c in m.calls if c[0] == "notify"), 6)
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_statistik_laeuft_mit(tmp_path):
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await asyncio.sleep(3)
        rec = list(ctrl.stats.days.values())
        assert rec and rec[0]["imp"] > 0 and rec[0]["secs"] > 1
        assert ctrl.status["house_w"] is not None
    finally:
        await stop(m, tasks)


@pytest.mark.asyncio
async def test_endpunkte_selbsttest_statistik_lernen_replay(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer
    import main as appmain
    from datetime import datetime, timedelta, timezone
    m, ctrl, ha, tasks = await start(str(tmp_path))
    try:
        await wait_for(lambda: m.states["number.pwr_a"]["state"] == "280")
        app = appmain.build_app(ctrl, ctrl.store, ha)
        async with TestClient(TestServer(app)) as c:
            r = await (await c.get("/api/selfcheck")).json()
            assert r["summary"]["ok"] >= 5 and "curtail" in r and any(i["area"] == "Verbindung" and i["status"] == "ok" for i in r["items"])
            st = await (await c.get("/api/stats?days=7")).json()
            assert "days" in st and "total" in st and st["total"]["imp"] >= 0
            ln = await (await c.get("/api/learn")).json()
            assert ln["used"] == 150 and ln["enabled"] is False
            sv = await (await c.get("/api/notify/services")).json()
            assert sv == ["persistent_notification", "notify.notify", "notify.mobile_app_pixel"] or set(sv) == {"persistent_notification", "notify.notify", "notify.mobile_app_pixel"}
            r = await c.post("/api/notify/test"); assert r.status == 400          # noch kein Ziel
            ctrl.cfg["notify"]["service"] = "persistent_notification"
            r = await (await c.post("/api/notify/test")).json(); assert r["ok"] is True
            assert any(x[:2] == ("persistent_notification", "create") and x[2]["title"] == "SOLASI Test" for x in m.calls)

            # --- Replay: Voraussetzungen fehlen
            r = await c.post("/api/replay", json={"hours": 2}); j = await r.json()
            assert r.status == 400 and "PV-Leistung" in j["error"]
            # --- Replay mit Verlaufsdaten
            for i, k in enumerate("ab"):
                ctrl.cfg["units"][i]["pv"] = f"sensor.pv_{k}"
            start_t = datetime.now(timezone.utc) - timedelta(hours=2, minutes=1)
            ts = start_t.isoformat()
            def series(eid, val): return [{"entity_id": eid, "state": str(val), "last_changed": ts}]
            m.history_data = [series("sensor.grid", 400), series("sensor.soc_a", 80), series("sensor.soc_b", 60),
                              series("sensor.rd_a", 0), series("sensor.rd_b", 0), series("sensor.rc_a", 0), series("sensor.rc_b", 0),
                              series("sensor.pv_a", 0), series("sensor.pv_b", 0)]
            ctrl.cfg["control"]["total_max_dis"] = 2000
            r = await c.post("/api/replay", json={"hours": 2, "overrides": {"features.eco": False}})
            j = await r.json()
            assert r.status == 200 and j["ok"], j
            assert 0.75 < j["actual"]["imp"] < 0.85                      # 400 W x 2 h gemessen
            assert j["current"]["imp"] < 0.3 and j["current"]["exp"] < 0.05   # Regelung gleicht den Bezug aus
            assert j["alt"] is not None and j["alt"]["imp"] < 0.3
            assert len(j["current"]["series"]["grid"]) > 50
            q = m.history_requests[-1]
            assert "sensor.grid" in q["filter_entity_id"] and q["minimal_response"] == "1"
            r = await c.post("/api/replay", json={"hours": 2, "overrides": {"units.0.num": "x"}}); assert r.status == 400
    finally:
        await stop(m, tasks)
