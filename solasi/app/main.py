"""SOLASI – Home-Assistant-Add-on (Ingress-Oberfläche + Regelung für Anker SOLIX)."""
import asyncio
import logging
import os
import signal
from datetime import datetime, timedelta, timezone

from aiohttp import web

import replay
import selfcheck
from controller import Controller, ConfigStore
from ha import HA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("solasi")

HERE = os.path.dirname(os.path.abspath(__file__))
HA_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
CONFIG_PATH = os.environ.get("SOLASI_CONFIG", "/data/settings.json")
PORT = int(os.environ.get("PORT", "8099"))
HA_API_URL = os.environ.get("HA_API_URL", "http://supervisor/core/api")


def read_version():
    """Version aus der Umgebung (Docker-Build), sonst aus config.yaml (Entwicklung/Tests), sonst „dev“."""
    v = os.environ.get("SOLASI_VERSION")
    if v:
        return v
    try:
        with open(os.path.join(HERE, "..", "config.yaml"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return "dev"


VERSION = read_version()
CARD_SRC = os.path.join(HERE, "card", "solasi-card.js")
# Mögliche Einhängepunkte der Home-Assistant-Konfiguration im Container
CONFIG_DIRS = os.environ.get("SOLASI_CONFIG_DIRS", "/homeassistant:/config:/ha_config").split(":")
CARD_BASE_URL = "/local/solasi/solasi-card.js"
# Ingress-Anfragen kommen ausschließlich vom Supervisor-Proxy
ALLOWED = {"172.30.32.2", "127.0.0.1", "::1"}
if os.environ.get("SOLASI_ALLOW_ALL"):
    ALLOWED = None


@web.middleware
async def guard(request, handler):
    if ALLOWED is not None and request.remote not in ALLOWED:
        return web.Response(status=403, text="Zugriff nur über Home Assistant")
    return await handler(request)


def card_text(src=CARD_SRC):
    """Dashboard-Karte mit eingesetzter Version."""
    with open(src, encoding="utf-8") as f:
        return f.read().replace("__VERSION__", VERSION)


def install_card(dirs=None, src=CARD_SRC):
    """Kopiert die Dashboard-Karte nach <config>/www/solasi/. Liefert (Zielpfad|None, www_neu_angelegt)."""
    for base in dirs or CONFIG_DIRS:
        if not os.path.isfile(os.path.join(base, "configuration.yaml")) and not os.path.isdir(os.path.join(base, ".storage")):
            continue
        www = os.path.join(base, "www")
        created = not os.path.isdir(www)
        try:
            target_dir = os.path.join(www, "solasi")
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, "solasi-card.js")
            with open(target, "w", encoding="utf-8") as f:
                f.write(card_text(src))
            return target, created
        except OSError as e:
            log.warning("Karte konnte nicht nach %s kopiert werden: %s", base, e)
    return None, False


def build_app(ctrl, store, ha):
    routes = web.RouteTableDef()

    @routes.get("/")
    async def index(_):
        return web.FileResponse(os.path.join(HERE, "static", "index.html"),
                                headers={"Cache-Control": "no-store"})

    @routes.get("/api/status")
    async def status(_):
        st = dict(ctrl.status)
        st.setdefault("connected", ha.connected)
        st["enabled"] = store.cfg["enabled"]
        st["dry_run"] = store.cfg["dry_run"]
        st["safety"] = dict(ctrl.safety)
        st["events"] = list(ctrl.events)[:80]
        return web.json_response(st)

    @routes.get("/api/config")
    async def get_config(_):
        return web.json_response(store.cfg)

    @routes.post("/api/config")
    async def set_config(request):
        try:
            data = await request.json()
            was_live = bool(store.cfg["enabled"]) and not store.cfg["dry_run"]
            store.save(data)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        ctrl.event("info", "Einstellungen gespeichert")
        now_live = bool(store.cfg["enabled"]) and not store.cfg["dry_run"]
        if was_live and not now_live and store.cfg["safety"]["release_on_disable"] and not ctrl.stopped:
            ctrl.event("info", "Live-Steuerung beendet: Speicher werden freigegeben")
            asyncio.create_task(ctrl.release_all("Steuerung ausgeschaltet", force=True))
        ctrl.wake.set()
        if ha.connected:
            asyncio.create_task(ctrl.sync_watchdog())
        return web.json_response({"ok": True})

    @routes.post("/api/kill")
    async def kill_api(_):
        did = await ctrl.kill("Von Hand gestoppt", "manual")
        return web.json_response({"ok": True, "stopped": ctrl.stopped, "changed": did})

    @routes.post("/api/resume")
    async def resume_api(_):
        did = ctrl.resume()
        return web.json_response({"ok": True, "stopped": ctrl.stopped, "changed": did})

    @routes.get("/api/watchdog")
    async def watchdog_api(_):
        return web.json_response(ctrl.watchdog)

    @routes.post("/api/watchdog/sync")
    async def watchdog_sync(_):
        return web.json_response(await ctrl.sync_watchdog())

    @routes.get("/api/device_sensors")
    async def device_sensors(request):
        return web.json_response(ha.device_sensors(request.query.get("entity", "")))

    @routes.get("/api/entity_options")
    async def entity_options(request):
        eid = request.query.get("entity", "")
        opts = ha.attr(eid, "options", []) if eid else []
        return web.json_response({"entity": eid, "state": ha.state(eid) if eid else None, "options": opts or []})

    @routes.get("/api/card")
    async def card(_):
        return web.json_response({**ctrl.card, "yaml": "type: custom:solasi-card\nentity: sensor.solasi"})

    @routes.get("/card.js")
    async def card_js(_):
        return web.Response(text=card_text(), content_type="text/javascript", charset="utf-8")

    @routes.get("/api/selfcheck")
    async def selfcheck_api(_):
        return web.json_response({**selfcheck.run(store.cfg, ha, ctrl), "curtail": ctrl.curtail})

    @routes.get("/api/stats")
    async def stats_api(request):
        try:
            days = max(1, min(int(request.query.get("days", 30)), 400))
        except ValueError:
            days = 30
        ctrl.stats.save()
        return web.json_response(ctrl.stats.summary(days, store.cfg["prices"]))

    @routes.get("/api/learn")
    async def learn_api(_):
        return web.json_response({**ctrl.learner.info(), "used": round(ctrl.base_load_effective()),
                                  "enabled": store.cfg["soc"]["learn_base_load"]})

    @routes.get("/api/notify/services")
    async def notify_services(_):
        try:
            services = await ha.get_services()
        except Exception:  # noqa: BLE001
            services = {}
        names = [f"notify.{s}" for s in services.get("notify", []) if s != "send_message"]
        return web.json_response(["persistent_notification"] + names)

    @routes.post("/api/notify/test")
    async def notify_test(_):
        if not store.cfg["notify"]["service"]:
            return web.json_response({"ok": False, "error": "Kein Ziel ausgewählt"}, status=400)
        ok = await ctrl.notifier.send("SOLASI Test", "Benachrichtigungen funktionieren. ☀️", "test")
        return web.json_response({"ok": ok})

    @routes.post("/api/replay")
    async def replay_api(request):
        try:
            body = await request.json()
            hours = max(1, min(int(body.get("hours", 24)), 72))
            overrides = body.get("overrides") or {}
            curtail = bool(body.get("curtail", False))
            cfg = store.cfg
            miss = replay.check_requirements(cfg)
            if miss:
                return web.json_response({"ok": False, "error": "Für den Replay fehlen: " + ", ".join(miss)}, status=400)
            cfg_alt = replay.apply_overrides(cfg, overrides) if overrides else None
            ids, units = replay.needed_entities(cfg)
            wanted = [e for e in (ids["grid"], ids["extra"], ids["house"]) if e]
            for u in units:
                wanted += [u[k] for k in ("soc", "rd", "rc", "pv", "power") if u[k]]
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=hours)
            raw = await ha.history(wanted, start, end)
            step = 10 if hours <= 24 else 20

            def work():
                data = replay.build_data(cfg, raw, start.timestamp(), end.timestamp(), step)
                return {"ok": True, "hours": replay.hours_label(data), "actual": replay.actual_metrics(data),
                        "current": replay.simulate(cfg, data, curtail=curtail),
                        "alt": replay.simulate(cfg_alt, data, curtail=curtail) if cfg_alt else None}

            return web.json_response(await asyncio.to_thread(work))
        except ValueError as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        except Exception as e:  # noqa: BLE001
            log.exception("Replay fehlgeschlagen")
            return web.json_response({"ok": False, "error": f"Replay fehlgeschlagen: {e}"}, status=500)

    @routes.get("/api/entities")
    async def entities(_):
        return web.json_response(ha.entities())

    app = web.Application(middlewares=[guard])
    app.add_routes(routes)
    return app


async def main():
    store = ConfigStore(CONFIG_PATH)
    ctrl = Controller(None, store)
    ha = HA(HA_URL, TOKEN, on_entity_event=lambda eid: ctrl.on_entity_event(eid),
            api_url=HA_API_URL, on_connected=lambda: ctrl.post_connect())
    ctrl.ha = ha
    target, created = install_card()
    full_url = f"{CARD_BASE_URL}?v={VERSION}"
    ctrl.card.update(installed=bool(target), target=target or "", url=full_url, base_url=CARD_BASE_URL,
                     restart_needed=created)
    if target:
        ctrl.event("info", f"Dashboard-Karte installiert ({target})")
        if created:
            ctrl.event("info", "Der Ordner www wurde neu angelegt: Home Assistant einmal neu starten, damit /local erreichbar ist")
    else:
        ctrl.event("info", "Dashboard-Karte konnte nicht automatisch installiert werden (siehe System → Dashboard-Karte)")
    runner = web.AppRunner(build_app(ctrl, store, ha))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Oberfläche läuft auf Port %d", PORT)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover
            pass
    tasks = [asyncio.create_task(ha.run()), asyncio.create_task(ctrl.run())]
    try:
        await stop.wait()
        log.info("Beende SOLASI …")
        await ctrl.shutdown()          # Speicher freigeben, solange die Verbindung noch steht
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        ctrl.stats.save()
        ctrl.learner.save()
        await ha.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
