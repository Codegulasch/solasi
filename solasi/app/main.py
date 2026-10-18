"""SOLASI – Home-Assistant-Add-on (Ingress-Oberfläche + Regelung für Anker SOLIX)."""
import asyncio
import logging
import os
import signal
from datetime import datetime, timedelta, timezone

from aiohttp import web

import copy
import accounts as acc

import discover
import goals
import hogs
import meterhist
import replay
import selfcheck
from controller import Controller, ConfigStore
from ha import HA
from util import data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("solasi")

HERE = os.path.dirname(os.path.abspath(__file__))
HA_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
CONFIG_PATH = os.environ.get("SOLASI_CONFIG", "/data/settings.json")
PORT = int(os.environ.get("PORT", "8099"))
DIRECT_PORT = int(os.environ.get("SOLASI_DIRECT_PORT", "8100"))
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


LOGIN_HTML = """<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SOLASI – Anmelden</title>
<style>body{font-family:system-ui,sans-serif;background:#f4f6f8;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}form{background:#fff;padding:28px;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.12);width:min(340px,92vw)}h1{margin:0 0 4px}p{color:#667;margin:0 0 16px;font-size:.9rem}input,button{width:100%;box-sizing:border-box;padding:12px;margin-top:10px;font-size:1rem;border-radius:10px;border:1px solid #ccd}button{background:#1b7f5c;color:#fff;border:0;font-weight:700;cursor:pointer}#e{color:#b00020;min-height:1.2em;margin-top:10px;font-size:.9rem}</style>
<form id="f"><h1>☀️ SOLASI</h1><p>__INFO__</p><input id="n" placeholder="Name" autocomplete="username" autofocus><input id="p" type="password" placeholder="Passwort" autocomplete="current-password"><button>Anmelden</button><div id="e"></div></form>
<script>f.onsubmit=async e=>{e.preventDefault();const r=await fetch("api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:n.value,password:p.value})});const j=await r.json();if(j.ok)location.reload();else e_.textContent=j.error};const e_=document.getElementById("e");</script></html>"""


def make_direct_middleware(accounts):
    @web.middleware
    async def direct_auth(request, handler):
        path = request.path
        if path in ("/api/login", "/api/logout"):
            return await handler(request)
        user = accounts.user_for(request.cookies.get("solasi_session"))
        if user is None and not accounts.has_any():
            user = {"name": "", "role": "owner"}        # ohne Konten: offener Zugang wie bei PrintDock (jeder im Netz = Besitzer)
        if user is None:
            if path.startswith("/api/") or path.endswith(".js"):
                return web.json_response({"ok": False, "error": "Bitte anmelden"}, status=401)
            return web.Response(text=LOGIN_HTML.replace("__INFO__", "Melde dich an."), content_type="text/html", headers={"Cache-Control": "no-store"})
        if not acc.allowed(user["role"], request.method, path):
            return web.json_response({"ok": False, "error": "Dafür fehlt deiner Rolle die Berechtigung"}, status=403)
        request["user"], request["role"] = user["name"], user["role"]
        return await handler(request)
    return direct_auth


def build_app(ctrl, store, ha, accounts=None, direct=False):
    routes = web.RouteTableDef()
    accounts = accounts if accounts is not None else acc.AccountStore(data_path("accounts.json"))

    @routes.post("/api/login")
    async def login(request):
        body = await request.json()
        tok, err = accounts.login(body.get("name"), body.get("password"), request.remote or "")
        if not tok:
            return web.json_response({"ok": False, "error": err}, status=429 if err and "Zu viele" in err else 401)
        r = web.json_response({"ok": True})
        r.set_cookie("solasi_session", tok, max_age=acc.SESSION_S, httponly=True, samesite="Lax")
        return r

    @routes.post("/api/logout")
    async def logout(request):
        accounts.logout(request.cookies.get("solasi_session"))
        r = web.json_response({"ok": True})
        r.del_cookie("solasi_session")
        return r

    @routes.get("/api/me")
    async def me(request):
        return web.json_response({"name": request.get("user") or ("Offener Zugang" if direct else "Home Assistant"),
                                  "role": request.get("role") or "owner", "direct": direct,
                                  "open": direct and not accounts.has_any(), "roles": acc.ROLES})

    @routes.get("/api/accounts")
    async def accounts_get(_):
        return web.json_response({"users": accounts.list(), "roles": acc.ROLES})

    @routes.post("/api/accounts")
    async def accounts_post(request):
        b = await request.json()
        name = str(b.get("name") or "")
        err = accounts.create(name, b.get("password"), b.get("role")) if b.get("create") else \
            (accounts.set_password(name, b["password"]) if b.get("password") else None) or \
            (accounts.set_role(name, b["role"]) if b.get("role") else None)
        if err:
            return web.json_response({"ok": False, "error": err}, status=400)
        ctrl.event("info", f"Konto „{name}“ " + ("angelegt" if b.get("create") else "geändert"))
        return web.json_response({"ok": True, "users": accounts.list()})

    @routes.delete("/api/accounts/{name}")
    async def accounts_del(request):
        name = request.match_info["name"]
        err = accounts.delete(name)
        if err:
            return web.json_response({"ok": False, "error": err}, status=400)
        ctrl.event("info", f"Konto „{name}“ gelöscht")
        return web.json_response({"ok": True, "users": accounts.list()})

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
        st["mode_id"] = goals.active_mode(store.cfg)
        m = goals.mode_by_id(store.cfg, st["mode_id"]) if st["mode_id"] else None
        st["mode_name"] = m["name"] if m else ""
        st["mode_icon"] = m.get("icon", "") if m else ""
        st["mode_effect"] = goals.effect(store.cfg, st.get("units"))
        return web.json_response(st)

    @routes.get("/api/defaults")
    async def defaults_get(_):
        """Vorlagen für neu angelegte Elemente (z. B. weiterer Speicher)."""
        from controller import default_unit
        return web.json_response({"unit": default_unit("Speicher")})

    @routes.get("/api/discover")
    async def discover_get(_):
        """Erkennt Speicher und Netz-Sensoren in Home Assistant (Einrichtungs-Assistent)."""
        return web.json_response(discover.discover(ha.states or {}, store.cfg))

    def _hog_filter(q):
        def iv(k, d=None):
            try:
                return int(q.get(k))
            except (TypeError, ValueError):
                return d
        wd = [int(x) for x in (q.get("wd") or "").split(",") if x.strip().isdigit() and 0 <= int(x) <= 6]
        return iv("days", 7), iv("from"), iv("to"), wd

    @routes.get("/api/hogs")
    async def hogs_get(request):
        """Rangliste der Stromfresser für Zeitraum, Uhrzeit und Wochentage."""
        days, tf, tt, wd = _hog_filter(request.query)
        devs = (store.cfg.get("hogs") or {}).get("devices") or []
        res = ctrl.hogs.rank(devs, days, tf, tt, wd, float((store.cfg.get("prices") or {}).get("import_ct", 35.0)))
        res["info"] = ctrl.hogs.info()
        res["configured"] = len(devs)
        res["profile"] = {d["id"]: ctrl.hogs.profile(d["id"], days, tf, tt, wd) for d in devs[:40]}
        return web.json_response(res)

    @routes.get("/api/hogs/curve")
    async def hogs_curve(request):
        q = request.query
        dev = q.get("dev") or ""
        ok = {d["id"] for d in (store.cfg.get("hogs") or {}).get("devices") or []} | {hogs.HOUSE}
        if dev not in ok:
            return web.json_response({"error": "unbekanntes Gerät"}, status=400)
        try:
            res = int(q.get("res") or 60)
            day = q.get("day") or None
            if day:
                datetime.strptime(day, "%Y-%m-%d")
            cmp_day = q.get("cmp") or None
            if cmp_day:
                datetime.strptime(cmp_day, "%Y-%m-%d")
        except ValueError:
            return web.json_response({"error": "ungültiger Parameter"}, status=400)
        out = {"dev": dev, "res": res, "points": ctrl.hogs.curve(dev, day, res)}
        if cmp_day:
            out["compare"] = ctrl.hogs.curve(dev, cmp_day, res)
        return web.json_response(out)

    @routes.get("/api/hogs/discover")
    async def hogs_discover(_):
        """Leistungssensoren (W/kW) in Home Assistant, die als Stromfresser in Frage kommen."""
        have = {d["power"] for d in (store.cfg.get("hogs") or {}).get("devices") or []}
        out = []
        for eid, st in (ha.states or {}).items():
            if not eid.startswith("sensor."):
                continue
            a = st.get("attributes") or {}
            if a.get("device_class") != "power" and a.get("unit_of_measurement") not in ("W", "kW"):
                continue
            if eid in have or eid.startswith("sensor.solasi_"):
                continue
            out.append({"entity": eid, "name": a.get("friendly_name") or eid, "w": st.get("state"), "unit": a.get("unit_of_measurement") or "W"})
        out.sort(key=lambda x: x["name"].lower())
        return web.json_response({"sensors": out[:300]})

    @routes.get("/api/locks")
    async def locks_get(_):
        return web.json_response({"locks": ctrl.lock_view()})

    @routes.post("/api/locks")
    async def locks_set(req):
        try:
            b = await req.json()
        except Exception:  # noqa: BLE001
            b = {}
        name = str(b.get("unit") or "")
        until = ctrl.until_from_time(b["until"]) if b.get("until") else 0
        ok = ctrl.set_lock(name, bool(b.get("on")), until, "Von Hand")
        if not ok:
            return web.json_response({"ok": False, "error": "Speicher unbekannt"}, status=400)
        await ctrl.publish_entities()
        return web.json_response({"ok": True, "locks": ctrl.lock_view()})

    @routes.get("/api/charge")
    async def charge_get(_):
        return web.json_response(ctrl.charge_view())

    @routes.post("/api/charge/estimate")
    async def charge_estimate(req):
        try:
            body = await req.json()
        except Exception:  # noqa: BLE001
            body = {}
        return web.json_response({"estimate": ctrl.charge_estimate(body)})

    @routes.post("/api/charge/start")
    async def charge_start(req):
        try:
            body = await req.json()
        except Exception:  # noqa: BLE001
            body = {}
        job, err = await ctrl.charge_start(body, "Oberfläche")
        if not job:
            return web.json_response({"ok": False, "error": err}, status=400)
        return web.json_response({"ok": True, **ctrl.charge_view()})

    @routes.post("/api/charge/stop")
    async def charge_stop(_):
        did = await ctrl.charge_stop("Von Hand beendet", "manual")
        return web.json_response({"ok": True, "changed": did})

    @routes.get("/api/phases")
    async def phases_get(_):
        return web.json_response({"view": ctrl.phases_view, "config": store.cfg.get("phases")})

    @routes.get("/api/phases/discover")
    async def phases_discover(_):
        import phases
        return web.json_response({"sensors": phases.discover(ha.states or {})})

    @routes.post("/api/phases/reset")
    async def phases_reset(_):
        """Erkennung der Einspeise-Phase von vorn beginnen."""
        ctrl.feed_det.reset()
        return web.json_response({"ok": True})

    @routes.get("/api/report")
    async def report_get(_):
        """Wochenbericht als Vorschau (so, wie er gesendet würde)."""
        import automation
        title, text = automation.weekly_report(ctrl.stats.summary(7, store.cfg.get("prices")))
        return web.json_response({"title": title, "text": text, "weekly": bool((store.cfg.get("reports") or {}).get("weekly"))})

    @routes.get("/api/goals")
    async def goals_get(_):
        return web.json_response(goals.snapshot(store.cfg))

    @routes.post("/api/goals/preview")
    async def goals_preview(request):
        """Berechnete Einzelwerte für Reglerstände, ohne zu speichern."""
        body = await request.json()
        g = goals.clean(body)
        cfg = copy.deepcopy(store.cfg)
        goals.apply(cfg, g)
        return web.json_response({"goals": g, "derived": goals.derive(g), "table": goals.table(cfg)})

    @routes.post("/api/goals/set")
    async def goals_set(request):
        """Einzelne Regler setzen (z. B. aus der Suche: „Reserve auf 40 %“); die übrigen bleiben wie sie sind."""
        body = await request.json()
        g = dict(goals.effective(store.cfg))
        for k in ("reserve", "precision", "care"):
            if k in body:
                g[k] = body[k]
        g = goals.clean(g)
        await ctrl.set_goals(g, who=request.get("user") or str(body.get("who") or ""))
        return web.json_response({"ok": True, **goals.snapshot(store.cfg)})

    @routes.post("/api/goals/mode")
    async def goals_mode(request):
        body = await request.json()
        m = await ctrl.activate_mode(str(body.get("id") or ""), who=request.get("user") or str(body.get("who") or ""))
        if not m:
            return web.json_response({"ok": False, "error": "Unbekannter Modus"}, status=404)
        return web.json_response({"ok": True, "mode": m["id"], **goals.snapshot(store.cfg)})

    @routes.post("/api/goals/custom")
    async def goals_custom(request):
        body = await request.json()
        mid = await ctrl.save_custom_mode(body.get("name"), body.get("icon"), body.get("goals") or goals.effective(store.cfg))
        if not mid:
            return web.json_response({"ok": False, "error": "Name fehlt"}, status=400)
        return web.json_response({"ok": True, "id": mid, **goals.snapshot(store.cfg)})

    @routes.delete("/api/goals/custom/{mid}")
    async def goals_custom_del(request):
        await ctrl.delete_custom_mode(request.match_info["mid"])
        return web.json_response({"ok": True, **goals.snapshot(store.cfg)})

    @routes.get("/api/config")
    async def get_config(_):
        return web.json_response(store.cfg)

    @routes.post("/api/config")
    async def set_config(request):
        try:
            data = await request.json()
            await ctrl.save_config(data)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        ctrl.event("info", "Einstellungen gespeichert")
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

    @routes.get("/api/mqtt")
    async def mqtt_api(_):
        return web.json_response({**ctrl.mqtt.status, "enabled": store.cfg["mqtt"]["enabled"]})

    @routes.get("/api/card")
    async def card(_):
        return web.json_response({**ctrl.card, "yaml": "type: custom:solasi-card\nentity: sensor.solasi"})

    @routes.get("/card.js")
    async def card_js(_):
        return web.Response(text=card_text(), content_type="text/javascript", charset="utf-8")

    @routes.get("/api/selfcheck")
    async def selfcheck_api(_):
        return web.json_response({**selfcheck.run(store.cfg, ha, ctrl), "curtail": ctrl.curtail})

    @routes.get("/api/meter_history")
    async def meter_history(request):
        eid = request.query.get("entity", "")
        known = [i.get("entity") for i in (store.cfg.get("meters") or {}).get("items", [])]
        if eid not in known:
            return web.json_response({"ok": False, "error": "Unbekannter Zähler"}, status=400)
        try:
            days = max(1, min(int(request.query.get("days", 30)), 120))
        except ValueError:
            days = 30
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days + 1)
        daily, source = {}, ""
        try:
            res = await ha.call({"type": "recorder/statistics_during_period", "start_time": start.isoformat(),
                                 "end_time": end.isoformat(), "statistic_ids": [eid], "period": "hour",
                                 "types": ["change"]}, timeout=40)
            daily = meterhist.daily_from_stats((res or {}).get(eid))
            source = "statistik"
        except Exception:  # noqa: BLE001
            daily = {}
        if not daily:
            try:
                raw = await ha.history([eid], start, end)
                daily = meterhist.daily_from_history(replay.parse_history(raw).get(eid))
                source = "verlauf"
            except Exception as e:  # noqa: BLE001
                return web.json_response({"ok": False, "error": f"Kein Verlauf verfügbar ({e})"}, status=502)
        st = ha.states.get(eid) or {}
        at = st.get("attributes") or {}
        return web.json_response({"ok": True, "entity": eid, "unit": at.get("unit_of_measurement") or "",
                                  "name": at.get("friendly_name") or eid, "source": source,
                                  "days": meterhist.fill(daily, days)})

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

    app = web.Application(middlewares=[make_direct_middleware(accounts)] if direct else [guard])
    app.add_routes(routes)
    return app


async def fetch_slug():
    """Eigener Add-on-Name beim Supervisor, damit die Karte die Oberfläche öffnen kann."""
    import aiohttp
    if not TOKEN:
        return ""
    try:
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {TOKEN}"}) as s:
            async with s.get(os.environ.get("SUPERVISOR_URL", "http://supervisor") + "/addons/self/info",
                             timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return ((await r.json()).get("data") or {}).get("slug", "")
    except Exception as e:  # noqa: BLE001
        log.info("Add-on-Name nicht abrufbar: %s", e)
    return ""


async def main():
    store = ConfigStore(CONFIG_PATH)
    ctrl = Controller(None, store)
    ha = HA(HA_URL, TOKEN, on_entity_event=lambda eid: ctrl.on_entity_event(eid),
            api_url=HA_API_URL, on_connected=lambda: ctrl.post_connect())
    ctrl.ha = ha
    ctrl.addon_slug = await fetch_slug()
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
    accounts = acc.AccountStore(data_path("accounts.json"))
    runner = web.AppRunner(build_app(ctrl, store, ha, accounts))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Oberfläche läuft auf Port %d", PORT)
    # Eigener Port mit Anmeldung: im Container immer bereit, von außen nur erreichbar, wenn in den Add-on-Einstellungen ein Port vergeben wird
    runner2 = web.AppRunner(build_app(ctrl, store, ha, accounts, direct=True))
    await runner2.setup()
    await web.TCPSite(runner2, "0.0.0.0", DIRECT_PORT).start()
    log.info("Direkter Zugang (mit Anmeldung) auf Port %d", DIRECT_PORT)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover
            pass
    ctrl.mqtt.version = VERSION
    ctrl.card_version = VERSION
    ctrl.mqtt.start()
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
        await ctrl.mqtt.stop()
        await ha.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
