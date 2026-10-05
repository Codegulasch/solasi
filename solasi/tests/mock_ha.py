"""Einfacher simulierter Home Assistant (WebSocket) für Integrationstests."""
import asyncio, json
from datetime import datetime, timezone
from aiohttp import web, WSMsgType


class MockHA:
    def __init__(self):
        self.states = {}
        self.calls = []
        self.subs = []  # (ws, id)
        self.runner = None
        self.port = None
        self.rest = {}          # entity_id -> {"state":..,"attributes":..}
        self.rest_posts = []    # Reihenfolge aller POSTs
        self.resources = []
        self.fail = set()       # (domain, service), die mit Fehler antworten sollen
        self.automations = {}
        self.automation_posts = []
        self.config_status = 200      # z. B. 403, um fehlende Rechte zu simulieren
        self.history_data = []
        self.history_requests = []
        self.api_url = None

    def set_state(self, eid, state, attrs=None, broadcast=True):
        now = datetime.now(timezone.utc).isoformat()
        new = {"entity_id": eid, "state": str(state), "attributes": attrs or self.states.get(eid, {}).get("attributes", {}),
               "last_changed": now, "last_updated": now, "last_reported": now}
        self.states[eid] = new
        if broadcast:
            asyncio.get_event_loop().create_task(self._broadcast(eid, new))

    def touch(self, eid):
        """Wert unverändert, nur last_reported ändert sich (kein Ereignis)."""
        self.states[eid]["last_reported"] = datetime.now(timezone.utc).isoformat()

    async def _broadcast(self, eid, new):
        for ws, sid in list(self.subs):
            try:
                await ws.send_json({"type": "event", "id": sid, "event": {
                    "event_type": "state_changed", "data": {"entity_id": eid, "new_state": new}}})
            except Exception:
                pass

    def _apply_service(self, domain, service, data):
        eid = data.get("entity_id")
        if domain == "number" and service == "set_value":
            self.set_state(eid, int(data["value"]) if float(data["value"]).is_integer() else data["value"])
        elif domain == "select" and service == "select_option":
            self.set_state(eid, data["option"])
            # Wechsel in den externen Modus macht die number-Entität verfügbar
            if data["option"] == "third_party_control":
                for k, v in list(self.states.items()):
                    if k.startswith("number.") and v["state"] == "unavailable" and k.endswith("_" + eid.split("_")[-1]):
                        self.set_state(k, 0)
        elif domain == "homeassistant" and service in ("turn_on", "turn_off"):
            self.set_state(eid, "on" if service == "turn_on" else "off")

    async def handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"type": "auth_required"})
        async for m in ws:
            if m.type != WSMsgType.TEXT:
                continue
            msg = json.loads(m.data)
            t = msg.get("type")
            if t == "auth":
                await ws.send_json({"type": "auth_ok" if msg.get("access_token") == "TOKEN" else "auth_invalid"})
            elif t == "get_states":
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": list(self.states.values())})
            elif t == "subscribe_events":
                if msg["event_type"] == "state_changed":
                    self.subs.append((ws, msg["id"]))
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": None})
            elif t == "get_config":
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": {"time_zone": "Europe/Berlin"}})
            elif t == "get_services":
                await ws.send_json({"id": msg["id"], "type": "result", "success": True,
                                    "result": {"notify": {"notify": {}, "mobile_app_pixel": {}, "send_message": {}},
                                               "persistent_notification": {"create": {}}}})
            elif t == "lovelace/resources":
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": list(self.resources)})
            elif t == "lovelace/resources/create":
                self.resources.append({"id": f"r{len(self.resources)+1}", "type": msg["res_type"], "url": msg["url"]})
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": self.resources[-1]})
            elif t == "lovelace/resources/update":
                for r in self.resources:
                    if r["id"] == msg["resource_id"]:
                        r["url"] = msg["url"]
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": {}})
            elif t == "call_service" and (msg["domain"], msg["service"]) in self.fail:
                await ws.send_json({"id": msg["id"], "type": "result", "success": False, "error": {"code": "failed", "message": "simulierter Fehler"}})
            elif t == "call_service":
                self.calls.append((msg["domain"], msg["service"], msg.get("service_data", {})))
                self._apply_service(msg["domain"], msg["service"], msg.get("service_data", {}))
                await ws.send_json({"id": msg["id"], "type": "result", "success": True, "result": {}})
        self.subs = [(w, i) for w, i in self.subs if w is not ws]
        return ws

    async def rest_state(self, request):
        if request.headers.get("Authorization") != "Bearer TOKEN":
            return web.Response(status=401)
        eid = request.match_info["eid"]
        body = await request.json()
        self.rest[eid] = body
        self.rest_posts.append(eid)
        return web.json_response(body, status=201)

    async def automation_endpoint(self, request):
        if request.headers.get("Authorization") != "Bearer TOKEN":
            return web.Response(status=401)
        if self.config_status != 200:
            return web.Response(status=self.config_status)
        aid = request.match_info["aid"]
        if request.method == "POST":
            body = await request.json()
            self.automations[aid] = body
            self.automation_posts.append(aid)
            self.set_state(f"automation.{aid}", "on", {"id": aid, "friendly_name": body.get("alias", "")})
            return web.json_response({"result": "ok"})
        if request.method == "DELETE":
            self.automations.pop(aid, None)
            st = self.states.pop(f"automation.{aid}", None)
            for ws, sid in list(self.subs):
                await ws.send_json({"type": "event", "id": sid, "event": {"event_type": "state_changed",
                                    "data": {"entity_id": f"automation.{aid}", "new_state": None}}})
            return web.json_response({"result": "ok"})
        return web.json_response(self.automations.get(aid, {}))

    async def history_endpoint(self, request):
        self.history_requests.append(dict(request.query))
        return web.json_response(self.history_data)

    async def start(self):
        app = web.Application()
        app.router.add_get("/api/history/period/{start}", self.history_endpoint)
        app.router.add_route("*", "/api/config/automation/config/{aid}", self.automation_endpoint)
        app.router.add_get("/websocket", self.handler)
        app.router.add_post("/api/states/{eid}", self.rest_state)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]
        self.api_url = f"http://127.0.0.1:{self.port}/api"
        return f"ws://127.0.0.1:{self.port}/websocket"

    async def stop(self):
        await self.runner.cleanup()
