"""Wächter-Automation, die SOLASI selbst in Home Assistant anlegt und aktuell hält.

Sie läuft unabhängig von SOLASI: Bleibt das Lebenszeichen (sensor.solasi_heartbeat) aus, stellt sie die Speicher auf
den Rückfall-Modus zurück, schaltet Fernsteuerungs-Schalter aus und schickt eine Meldung. Beim Beenden durch den Nutzer
setzt SOLASI das Lebenszeichen auf „stopped“, dann greift der Wächter nicht ein (die Speicher sind ja schon freigegeben).
"""
import hashlib
import json
import logging

import drivers

log = logging.getLogger("solasi.watchdog")

AUTOMATION_ID = "solasi_waechter"
HEARTBEAT = "sensor.solasi_heartbeat"


def _unit_actions(u, names):
    """Statische Rückstell-Aktionen für einen Speicher."""
    d, o, k = drivers.driver(u), drivers.opts(u, names), u.get("name", "Speicher")
    acts = []

    def select(entity, option):
        if entity and option:
            acts.append({
                "if": [{"condition": "template", "value_template": f"{{{{ not is_state('{entity}', '{option}') }}}}"}],
                "then": [{"service": "select.select_option", "target": {"entity_id": entity}, "data": {"option": option}}],
                "continue_on_error": True,
            })

    if d == "modal":
        select(u.get("dir"), o["stop"])
    elif d == "limit":
        fv = u.get("fallback_value")
        try:
            if fv not in ("", None):
                acts.append({"service": "number.set_value", "target": {"entity_id": u["num"]}, "data": {"value": float(fv)},
                             "continue_on_error": True})
        except (TypeError, ValueError):
            pass
    elif d == "script" and u.get("script"):
        acts.append({"service": "script.turn_on", "target": {"entity_id": u["script"]},
                     "data": {"variables": {"power_w": 0, "mode": "release", "unit": k}}, "continue_on_error": True})
    if d != "script":
        select(u.get("mode"), u.get("fallback_mode"))
    return acts


def build(cfg):
    """Liefert (automation_dict | None, hinweis)."""
    sf = cfg["safety"]
    if not sf.get("watchdog", True):
        return None, "ausgeschaltet"
    names = cfg["names"]
    actions, switches = [], []
    for u in cfg["units"]:
        if not drivers.configured(u):
            continue
        ua = _unit_actions(u, names)
        if not ua and not u.get("enable"):
            continue
        actions += ua
        if u.get("enable"):
            switches.append(u["enable"])
    if not actions and not switches:
        return None, "nicht nötig: kein Speicher hat einen Rückfall-Modus oder eine Fernsteuerung"
    timeout_s = max(float(sf.get("watchdog_min", 3)), 1) * 60
    wait_min = 8
    if switches:
        actions.append({"service": "homeassistant.turn_off", "target": {"entity_id": sorted(set(switches))}, "continue_on_error": True})
    service = cfg["notify"]["service"]
    if service:
        svc = "persistent_notification.create" if service == "persistent_notification" else service
        actions.append({"service": svc, "continue_on_error": True,
                        "data": {"title": "⛔ SOLASI-Wächter hat die Speicher zurückgesetzt",
                                 "message": "{{ why }}. Die Speicher laufen wieder im eigenen Modus."}})
    auto = {
        "id": AUTOMATION_ID,
        "alias": "SOLASI Wächter",
        "description": "Wird von SOLASI automatisch verwaltet und bei Änderungen der Einstellungen aktualisiert. "
                       "Stellt die Speicher zurück, wenn SOLASI ausfällt.",
        "mode": "single",
        "trigger": [
            {"platform": "template", "id": "stale",
             "value_template": f"{{% set s = states['{HEARTBEAT}'] %}}"
                               f"{{{{ s is not none and s.state not in ['unavailable', 'unknown', 'stopped'] "
                               f"and (now() - s.last_updated).total_seconds() > {int(timeout_s)} }}}}"},
            {"platform": "homeassistant", "event": "start", "id": "boot"},
        ],
        "condition": [],
        "action": [
            {"choose": [{
                "conditions": [{"condition": "trigger", "id": "boot"}],
                "sequence": [
                    {"wait_template": f"{{{{ states('{HEARTBEAT}') not in ['unavailable', 'unknown', 'none'] }}}}",
                     "timeout": {"minutes": wait_min}, "continue_on_timeout": True},
                    {"condition": "template", "value_template": "{{ not wait.completed }}"},
                ]}]},
            {"variables": {"why": "{{ 'SOLASI hat sich nach dem Start von Home Assistant nicht gemeldet' if trigger.id == 'boot' "
                                  "else 'SOLASI sendet kein Lebenszeichen mehr' }}"}},
            *actions,
        ],
    }
    return auto, "ok"


def digest(auto):
    return hashlib.sha256(json.dumps(auto, sort_keys=True).encode()).hexdigest()[:16]


def pretty(auto):
    """JSON ist gültiges YAML und lässt sich im YAML-Editor von Home Assistant einfügen."""
    return json.dumps(auto, indent=2, ensure_ascii=False)


async def sync(ctrl):
    """Legt die Automation an, aktualisiert oder löscht sie. Setzt ctrl.watchdog (Zustand für die Oberfläche)."""
    cfg, ha = ctrl.cfg, ctrl.ha
    auto, note = build(cfg)
    st = {"state": "aus", "detail": note, "json": "", "managed": False}
    ctrl.watchdog = st
    present = any(e.get("attributes", {}).get("id") == AUTOMATION_ID
                  for eid, e in ha.states.items() if eid.startswith("automation."))
    if auto is None:
        st["state"] = "aus" if note == "ausgeschaltet" else "nicht nötig"
        if ctrl._wd_hash:                                 # von uns angelegt: wieder entfernen
            try:
                await ha.config_request("DELETE", f"config/automation/config/{AUTOMATION_ID}")
                ctrl.event("info", "Wächter-Automation entfernt")
            except Exception as e:  # noqa: BLE001
                log.info("Wächter konnte nicht entfernt werden: %s", e)
        ctrl._set_wd_hash("")
        return st
    st["json"] = pretty(auto)
    h = digest(auto)
    if present and ctrl._wd_hash == h:
        st.update(state="aktiv", detail="angelegt und aktuell", managed=True)
        return st
    was_ours = bool(ctrl._wd_hash)
    try:
        await ha.config_request("POST", f"config/automation/config/{AUTOMATION_ID}", auto)
        ctrl._set_wd_hash(h)
        st.update(state="aktiv", detail="aktualisiert" if was_ours else "angelegt", managed=True)
        ctrl.event("info", f"Wächter-Automation {st['detail']}")
    except Exception as e:  # noqa: BLE001
        st.update(state="manuell", detail=f"Automatisch nicht möglich ({e}). Den Text unten als Automation einfügen.")
        ctrl.event("info", "Wächter-Automation konnte nicht automatisch angelegt werden (siehe Sicherheit & Meldungen)")
    return st

