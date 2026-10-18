"""Ziele und Modi: drei Regler in Alltagssprache, aus denen die Einzelwerte berechnet werden.

reserve   (0..100)  Reserve für den Abend: wie viel Akku bleibt übrig (Mindest-Ladestand)
precision (0..100)  Netzbezug vermeiden: wie genau auf Null geregelt wird
care      (0..100)  Akku schonen: weniger tief entladen, nicht immer ganz voll laden

Die Berechnung ist rein und hat keine Seiteneffekte. Die Oberfläche zeigt Aktuell und Berechnet nebeneinander und
markiert Werte, die von Hand abweichen, als „angepasst“.
"""
import copy

KEYS = ("reserve", "precision", "care")

# Modi: Name, Symbol, Beschreibung, Regler
PRESETS = [
    {"id": "balanced", "name": "Ausgewogen", "icon": "⚖️", "text": "Nulleinspeisung, Reserve für die Nacht",
     "reserve": 50, "precision": 70, "care": 30},
    {"id": "autarky", "name": "Max. Autarkie", "icon": "🌱", "text": "Akku so leer wie möglich, Netz meiden",
     "reserve": 10, "precision": 90, "care": 10},
    {"id": "care", "name": "Akku schonen", "icon": "🔋", "text": "Weniger tief, nicht immer voll",
     "reserve": 60, "precision": 50, "care": 90},
    {"id": "holiday", "name": "Urlaub", "icon": "🏖️", "text": "Reserve hoch, ruhiger Betrieb",
     "reserve": 80, "precision": 30, "care": 60},
    {"id": "emergency", "name": "Notstrom", "icon": "🛟", "text": "Reserve schützen, nichts abgeben",
     "reserve": 100, "precision": 50, "care": 0},
]

# Pfade in der Konfiguration, die aus den Reglern berechnet werden (Beschriftung für die Tabelle „Alle Werte einzeln“)
FIELDS = [
    ("soc.min", "Mindest-Ladestand", "%"),
    ("soc.max", "Höchst-Ladestand", "%"),
    ("soc.hyst", "Hysterese Ladestand", "%"),
    ("soc.eco_threshold", "Eco-Schwelle", "%"),
    ("control.min_gap", "Mindestabstand Schreiben", "s"),
    ("control.offset_discharge", "Sicherheitsabstand Entladen", "W"),
]


def clamp(v, lo=0, hi=100):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def clean(g):
    """Regler auf 0..100 begrenzen (fehlende Werte: Standard „Ausgewogen“)."""
    base = PRESETS[0]
    g = g if isinstance(g, dict) else {}
    return {k: int(round(clamp(g.get(k, base[k])))) for k in KEYS}


def derive(g):
    """Regler -> Einzelwerte (Pfad -> Wert)."""
    g = clean(g)
    r, p, c = g["reserve"], g["precision"], g["care"]
    smin = int(round(5 + r * 0.4 + c * 0.05))
    smin = min(smin, 95)
    smax = max(smin + 5, 100 - int(round(c * 0.2)))
    smax = min(smax, 100)
    return {
        "soc.min": smin,
        "soc.max": smax,
        "soc.hyst": int(round(3 + c / 25)),
        "soc.eco_threshold": min(smin + 20, 90),
        "control.min_gap": int(round(10 - 7 * p / 100)),
        "control.offset_discharge": int(round(30 * (1 - p / 100))),
    }


def estimate(cfg):
    """Regler aus den aktuellen Einzelwerten schätzen (für Installationen, in denen noch kein Regler gesetzt wurde)."""
    soc = cfg.get("soc", {})
    ctl = cfg.get("control", {})
    smax = soc.get("max", 99)
    c = clamp((100 - smax) / 0.2)
    r = clamp((soc.get("min", 15) - 5 - c * 0.05) / 0.4)
    p = clamp((10 - ctl.get("min_gap", 5)) / 7 * 100)
    return {"reserve": int(round(r)), "precision": int(round(p)), "care": int(round(c))}


def effective(cfg):
    """Die Regler, wie sie die Oberfläche zeigt: gespeicherte, sonst geschätzte."""
    g = cfg.get("goals") or {}
    if all(g.get(k) is not None for k in KEYS):
        return clean(g)
    return estimate(cfg)


def get_path(cfg, path):
    o = cfg
    for k in path.split("."):
        o = o.get(k) if isinstance(o, dict) else None
    return o


def set_path(cfg, path, v):
    ks = path.split(".")
    o = cfg
    for k in ks[:-1]:
        o = o.setdefault(k, {})
    o[ks[-1]] = v


def table(cfg):
    """Zeilen für „Alle Werte einzeln“: aktuell, berechnet, Status (wie berechnet / angepasst)."""
    want = derive(effective(cfg))
    rows = []
    for path, label, unit in FIELDS:
        cur = get_path(cfg, path)
        rows.append({"path": path, "label": label, "unit": unit, "current": cur, "derived": want[path],
                     "custom": cur != want[path]})
    return rows


def all_modes(cfg):
    out = [dict(m) for m in PRESETS]
    for m in cfg.get("modes") or []:
        if isinstance(m, dict) and m.get("id") and m.get("name"):
            out.append({"id": str(m["id"])[:40], "name": str(m["name"])[:30], "icon": str(m.get("icon") or "⭐")[:4],
                        "text": str(m.get("text") or "Eigener Modus")[:80], "custom": True, **{k: int(clamp(m.get(k, 50))) for k in KEYS}})
    return out


def apply(cfg, g, mode=""):
    """Schreibt Regler und berechnete Einzelwerte in die Konfiguration (verändert cfg). -> Liste der Änderungen."""
    g = clean(g)
    changes = []
    for path, v in derive(g).items():
        old = get_path(cfg, path)
        if old != v:
            changes.append((path, old, v))
        set_path(cfg, path, v)
    cfg["goals"] = {"mode": mode, **g}
    return changes


def mode_by_id(cfg, mid):
    return next((m for m in all_modes(cfg) if m["id"] == mid), None)


def active_mode(cfg):
    """Name des aktiven Modus: gespeichert und noch passend, sonst leer („Eigene Einstellung“)."""
    g = cfg.get("goals") or {}
    mid = g.get("mode")
    m = mode_by_id(cfg, mid) if mid else None
    if not m:
        return None
    if any(get_path(cfg, p) != v for p, v in derive(m).items()):
        return None            # Einzelwerte wurden von Hand verändert -> kein reiner Modus mehr
    return m["id"]


def effect(cfg, units=None):
    """Was bewirken die aktuellen Grenzen gerade? -> {head, units: [{name, soc, state, text}], note}. Reine Beschreibung, steuert nichts."""
    so = cfg.get("soc") or {}
    lo, hi = so.get("min", 15), so.get("max", 99)
    rows = []
    for u in units or []:
        soc = u.get("soc")
        if soc is None or soc < 0 or u.get("paused"):
            continue
        n = u.get("name") or "Speicher"
        if soc >= hi:
            rows.append({"name": n, "soc": soc, "state": "full", "text": f"{n} ({soc} %) ist voll (ab {hi} %) – lädt nicht weiter, gibt ab."})
        elif soc <= lo:
            rows.append({"name": n, "soc": soc, "state": "low", "text": f"{n} ({soc} %) liegt unter {lo} % – gibt nichts ab, nur die eigene Solarleistung geht ins Haus."})
        else:
            rows.append({"name": n, "soc": soc, "state": "ok", "text": f"{n} ({soc} %) darf abgeben, bis {lo} % erreicht sind."})
    return {"head": f"Gibt ab bis {lo} %, lädt bis {hi} %",
            "units": rows,
            "note": "Geladen wird nur bei Überschuss (Solar größer als Verbrauch, bzw. Einspeisung). SOLASI lädt nicht aus dem Netz nach – ein Modus setzt Grenzen, er erzwingt kein Laden."}


def snapshot(cfg):
    modes = [dict(m, derived=derive(m)) for m in all_modes(cfg)]
    return {"goals": effective(cfg), "derived": derive(effective(cfg)), "mode": active_mode(cfg), "modes": modes, "table": table(cfg),
            "set": copy.deepcopy(cfg.get("goals") or {})}
