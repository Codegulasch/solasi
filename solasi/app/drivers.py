"""Treiber für unterschiedliche Speichertypen.

Die Regelung arbeitet intern mit einem vorzeichenbehafteten Sollwert pro Speicher
(positiv = Entladen ins Haus, negativ = Laden aus dem Netz). Ein Treiber übersetzt das in Befehle:

anker    Zahl für den Betrag + Auswahl für die Richtung (Anker SOLIX mit der offiziellen Integration)
signed   eine Zahl mit Vorzeichen (z. B. Marstek im Passiv-Modus)
modal    Auswahl für den Modus (Stop/Laden/Entladen) + je eine Zahl für Lade- und Entladeleistung (z. B. Marstek Modbus)
limit    eine Zahl als Ausgangslimit, nur Entladen (z. B. Wechselrichter-Limit)
script   ruft ein Home-Assistant-Skript auf (für alles andere)

Alle Funktionen hier sind frei von Seiteneffekten. Die Befehle werden vom Controller ausgeführt.
"""
from ha import is_num, num

DRIVER_IDS = ("anker", "signed", "modal", "limit", "script")


def driver(u):
    d = u.get("driver", "anker")
    return d if d in DRIVER_IDS else "anker"


def configured(u):
    d = driver(u)
    if d == "anker":
        return bool(u.get("num") and u.get("dir"))
    if d in ("signed", "limit"):
        return bool(u.get("num"))
    if d == "modal":
        return bool(u.get("dir") and u.get("num"))
    return bool(u.get("script"))


def can_charge(u):
    """Kann der Speicher aus dem Netz laden?"""
    d = driver(u)
    if d == "limit":
        return False
    if d == "modal" and not u.get("num_chg"):
        return False
    return bool(u.get("can_charge", True))


def curtail_enabled(u):
    """Darf bei vollem Speicher „Entladen mit 0 W“ erzwungen werden?"""
    return driver(u) in ("anker", "modal") and bool(u.get("curtail", True))


def opts(u, names):
    d = driver(u)
    return {
        "dis": u.get("dir_dis") or names["dis"],
        "chg": u.get("dir_chg") or names["chg"],
        "stop": u.get("dir_stop") or "stop",
        "mode": u.get("mode_option") or (names["mode_option"] if d == "anker" else ""),
    }


def entities(u):
    """Alle Entitäten, die zum Steuern gebraucht werden (für Prüfungen)."""
    return [e for e in (u.get("num"), u.get("num_chg"), u.get("dir"), u.get("script"), u.get("mode"), u.get("enable")) if e]


# ---------------------------------------------------------------- Lesen
def read(ha, u, names, memory=None):
    """Aktueller Zustand des Speichers aus Sicht des Treibers."""
    d, o = driver(u), opts(u, names)
    mode_s = ha.state(u["mode"]) if u.get("mode") else None
    out = {"has": False, "set": 0.0, "dir": None, "mode": mode_s, "num_state": None}
    if d == "script":
        out["has"] = True
        out["set"] = float((memory or {}).get(u.get("name"), 0.0))
        return out
    n = ha.state(u["num"]) if u.get("num") else None
    out["num_state"] = n
    if d == "anker":
        ds = ha.state(u["dir"])
        out["dir"] = ds
        out["has"] = is_num(n)
        mag = num(n) if out["has"] else 0.0
        out["set"] = (mag if ds == o["dis"] else -mag) if out["has"] else 0.0
    elif d == "signed":
        out["has"] = is_num(n)
        v = num(n) if out["has"] else 0.0
        out["set"] = v if u.get("sign", "discharge_positive") == "discharge_positive" else -v
    elif d == "limit":
        out["has"] = is_num(n)
        out["set"] = max(num(n), 0.0) if out["has"] else 0.0
    elif d == "modal":
        fm = ha.state(u["dir"])
        out["dir"] = fm
        nc = ha.state(u["num_chg"]) if u.get("num_chg") else None
        out["has"] = is_num(n) and fm not in (None, "unavailable", "unknown") and (not u.get("num_chg") or is_num(nc))
        if out["has"]:
            if fm == o["dis"]:
                out["set"] = num(n)
            elif fm == o["chg"]:
                out["set"] = -num(nc)
    return out


def sensor_num(ha, eid):
    """Zahl aus einem Sensor. Fehlt der Sensor oder ist er nicht verfügbar, kommt None (unbekannt), nie 0."""
    if not eid:
        return None
    s = ha.state(eid)
    return num(s) if is_num(s) else None


def basis(u):
    """Was messen die gewählten Leistungssensoren? "ac" = Leistung am Hausanschluss des Speichers,
    "battery" = Leistung an der Batterie (DC). Automatisch: Anker mit PV-Sensor misst an der Batterie."""
    b = u.get("power_basis") or ""
    if b in ("ac", "battery"):
        return b
    return "battery" if (driver(u) == "anker" and u.get("pv")) else "ac"


def flows(ha, u):
    """Leistungsflüsse eines Speichers in W (None = unbekannt).

    pv   Solarleistung der angeschlossenen Module
    bat  Batterie netto: positiv = Entladen, negativ = Laden
    ac   Abgabe an das Haus: positiv = ins Haus, negativ = Netzladen

    Bei Hybrid-Speichern (PV an der Batterieseite, z. B. Anker) gilt: ac = pv + bat. Beispiel: 540 W PV, Batterie lädt 140 W
    -> 400 W gehen ins Haus."""
    pv = sensor_num(ha, u.get("pv"))
    if u.get("power"):
        v = sensor_num(ha, u["power"])
        net = None if v is None else v * (1 if u.get("power_sign", "discharge_positive") == "discharge_positive" else -1)
        has = True
    elif u.get("real_dis") or u.get("real_chg"):
        d = sensor_num(ha, u.get("real_dis")) if u.get("real_dis") else 0.0
        c = sensor_num(ha, u.get("real_chg")) if u.get("real_chg") else 0.0
        net = None if (d is None or c is None) else d - c
        has = True
    else:
        return {"has": False, "pv": pv, "bat": None, "ac": None, "basis": basis(u)}
    b = basis(u)
    if net is None:
        bat = ac = None
    elif b == "battery":
        bat = net
        ac = None if pv is None else pv + net
    else:
        ac = net
        bat = (ac - pv) if pv is not None else net
    return {"has": has, "pv": pv, "bat": bat, "ac": ac, "basis": b}


# ---------------------------------------------------------------- Schreiben
def _clamp(ha, entity, value):
    lo, hi = ha.attr(entity, "min"), ha.attr(entity, "max")
    if isinstance(lo, (int, float)):
        value = max(value, lo)
    if isinstance(hi, (int, float)):
        value = min(value, hi)
    return value


def guard_commands(u, names, ha):
    """Befehle, die vor dem Steuern nötig sind (Fernsteuerung einschalten, Arbeitsmodus setzen)."""
    cmds = []
    if driver(u) == "script":
        return cmds
    o = opts(u, names)
    k = u.get("name", "Speicher")
    unusable = (None, "unavailable", "unknown")      # nicht erreichbare Entitäten lassen sich nicht schalten
    if u.get("enable") and ha.state(u["enable"]) not in unusable and ha.state(u["enable"]) != "on":
        cmds.append(("homeassistant", "turn_on", {"entity_id": u["enable"]}, f"{k}: Fernsteuerung einschalten"))
    if u.get("mode") and o["mode"] and ha.state(u["mode"]) not in unusable and ha.state(u["mode"]) != o["mode"]:
        cmds.append(("select", "select_option", {"entity_id": u["mode"], "option": o["mode"]},
                     f"{k}: Modus auf '{o['mode']}' setzen"))
    return cmds


def needs_write(u, s, p, force, step, real_fix, names):
    """Muss etwas gesendet werden?"""
    d, o = driver(u), opts(u, names)
    cur = s["set"]
    if abs(p - cur) >= step or (p == 0 and cur != 0) or real_fix:
        return True
    if p == 0 and force and d in ("anker", "modal") and s["dir"] != o["dis"]:
        return True
    return False


def label(p, force):
    if p > 0:
        return "Entladen"
    if p < 0:
        return "Laden"
    return "Entladen 0 W (Abregelung)" if force else "Aus"


def commands(u, s, p, force, names, ha):
    """Befehle (Dienst, Daten, Beschreibung), die den Sollwert p herstellen."""
    d, o, k = driver(u), opts(u, names), u.get("name", "Speicher")
    cur = s["set"]
    cmds = []
    if d == "anker":
        want = o["dis"] if (p > 0 or (force and p == 0)) else (o["chg"] if p < 0 else "")
        if want and s["dir"] != want:
            if cur != 0:
                cmds.append(("number", "set_value", {"entity_id": u["num"], "value": 0}, f"{k}: Leistung auf 0 (vor Richtungswechsel)"))
            cmds.append(("select", "select_option", {"entity_id": u["dir"], "option": want}, f"{k}: Richtung → {want}"))
        cmds.append(("number", "set_value", {"entity_id": u["num"], "value": _clamp(ha, u["num"], abs(int(p)))},
                     f"{k}: {cur:.0f} W → {abs(p)} W ({label(p, force)})"))
    elif d == "signed":
        v = p if u.get("sign", "discharge_positive") == "discharge_positive" else -p
        cmds.append(("number", "set_value", {"entity_id": u["num"], "value": _clamp(ha, u["num"], int(v))},
                     f"{k}: {cur:.0f} W → {p} W ({label(p, force)})"))
    elif d == "limit":
        cmds.append(("number", "set_value", {"entity_id": u["num"], "value": _clamp(ha, u["num"], max(int(p), 0))},
                     f"{k}: Ausgangslimit {cur:.0f} W → {max(p, 0)} W"))
    elif d == "modal":
        has_chg = bool(u.get("num_chg"))
        pd, pc = (int(p) if p > 0 else 0), (int(-p) if p < 0 else 0)
        if p > 0 or (force and p == 0):
            mode = o["dis"]
        elif p < 0:
            mode = o["chg"]
        else:
            mode = o["stop"]
        # erst die Leistungen, dann den Modus (so reagieren die Geräte am zuverlässigsten)
        if has_chg:
            cmds.append(("number", "set_value", {"entity_id": u["num_chg"], "value": _clamp(ha, u["num_chg"], pc)},
                         f"{k}: Ladeleistung {pc} W"))
        cmds.append(("number", "set_value", {"entity_id": u["num"], "value": _clamp(ha, u["num"], pd)},
                     f"{k}: Entladeleistung {pd} W"))
        if s["dir"] != mode:
            cmds.append(("select", "select_option", {"entity_id": u["dir"], "option": mode}, f"{k}: Modus → {mode}"))
    elif d == "script":
        mode = "discharge" if p > 0 else ("charge" if p < 0 else "idle")
        cmds.append(("script", "turn_on", {"entity_id": u["script"],
                                           "variables": {"power_w": int(p), "mode": mode, "unit": k}},
                     f"{k}: Skript mit {int(p)} W ({mode})"))
    return cmds


def release_commands(u, s, names, ha):
    """Befehle, die den Speicher an sein eigenes Regelverhalten zurückgeben (z. B. Eigenverbrauch).

    Reihenfolge: zuerst Leistung auf 0 bzw. Stop (solange der Speicher noch im externen Modus ist),
    dann Fernsteuerung aus, zuletzt den Rückfall-Modus setzen."""
    d, o, k = driver(u), opts(u, names), u.get("name", "Speicher")
    cmds = []
    if d == "anker":
        if s["has"] and s["set"] != 0:
            cmds.append(("number", "set_value", {"entity_id": u["num"], "value": 0}, f"{k}: Leistung auf 0"))
    elif d == "signed":
        if s["has"] and s["set"] != 0:
            cmds.append(("number", "set_value", {"entity_id": u["num"], "value": 0}, f"{k}: Leistung auf 0"))
    elif d == "modal":
        if u.get("num_chg") and is_num(ha.state(u["num_chg"])) and num(ha.state(u["num_chg"])) != 0:
            cmds.append(("number", "set_value", {"entity_id": u["num_chg"], "value": 0}, f"{k}: Ladeleistung auf 0"))
        if is_num(ha.state(u["num"])) and num(ha.state(u["num"])) != 0:
            cmds.append(("number", "set_value", {"entity_id": u["num"], "value": 0}, f"{k}: Entladeleistung auf 0"))
        if s["dir"] != o["stop"]:
            cmds.append(("select", "select_option", {"entity_id": u["dir"], "option": o["stop"]}, f"{k}: Modus → {o['stop']}"))
    elif d == "limit":
        fv = u.get("fallback_value")
        if fv not in ("", None) and is_num(fv):
            cmds.append(("number", "set_value", {"entity_id": u["num"], "value": _clamp(ha, u["num"], float(fv))},
                         f"{k}: Ausgangslimit auf {fv} W"))
    elif d == "script":
        cmds.append(("script", "turn_on", {"entity_id": u["script"], "variables": {"power_w": 0, "mode": "release", "unit": k}},
                     f"{k}: Skript mit mode=release"))
    if u.get("enable") and ha.state(u["enable"]) == "on":
        cmds.append(("homeassistant", "turn_off", {"entity_id": u["enable"]}, f"{k}: Fernsteuerung ausschalten"))
    fb = u.get("fallback_mode")
    if u.get("mode") and fb and ha.state(u["mode"]) != fb:
        cmds.append(("select", "select_option", {"entity_id": u["mode"], "option": fb}, f"{k}: Modus → {fb}"))
    return cmds
