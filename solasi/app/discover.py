"""Geräte-Erkennung: sucht in den Home-Assistant-Entitäten nach Speichern und Zählern und schlägt eine Einrichtung vor.

Gearbeitet wird nur mit Namen (friendly_name, sonst Entitäts-ID): Ein Gerät ist die Gruppe von Entitäten, die vor dem
Stichwort („Ladestand“, „Leistungsfluss“ …) denselben Namen tragen, z. B. „Anker Solix 4 HÜTTE Ladestand“ und
„Anker Solix 4 HÜTTE Leistungsfluss“ -> Gerät „Anker Solix 4 HÜTTE“. Das ist eine Hilfe zum Vorausfüllen; der Nutzer
bestätigt oder ändert jedes Feld.
"""
import re

# Feld -> (Domänen, Muster auf dem kleingeschriebenen Namen)
PATTERNS = [
    ("lim_res", ("number",), r"notstrom|emergency|backup.?reserve|reserve"),
    ("lim_dis", ("number",), r"entladegrenze|entlade.?soc|discharge.?(limit|soc)|min(imum)?.?soc"),
    ("lim_chg", ("number",), r"ladeobergrenze|ladegrenze|lade.?soc|charge.?(limit|soc)|max(imum)?.?soc"),
    ("num", ("number",), r"leistungssteuerung|power.?control|output.?power.?control|ausgangsleistung"),
    ("dir", ("select",), r"leistungsfluss|power.?flow|flow.?direction"),
    ("mode", ("select",), r"betriebsmodus|working.?mode|usage.?mode|betriebsart|operating.?mode"),
    ("soc", ("sensor",), r"ladestand|state.?of.?charge|\bsoc\b|battery.?level|akkustand|batterie.?stand|ladezustand"),
    ("pv", ("sensor",), r"(solar|pv).{0,20}(leistung|power)|(leistung|power).{0,20}(solar|pv)"),
]
GRID_RE = re.compile(r"netz|grid|zähler|zaehler|smart.?meter|einspeis|bezug|p1|tibber|shelly.*total|power.?meter", re.I)
CLEAN = " -_:·.,"


def _name(eid, st):
    n = (st.get("attributes") or {}).get("friendly_name") or eid.split(".", 1)[1].replace("_", " ")
    return str(n).strip()


def _num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def find_units(states, configured=()):
    """-> Liste von Vorschlägen für Speicher: {name, driver, num, dir, mode, soc, pv, lim_*, found, configured}."""
    groups = {}
    for eid, st in states.items():
        dom = eid.split(".", 1)[0]
        name = _name(eid, st)
        low = name.lower()
        for field, doms, pat in PATTERNS:
            if dom not in doms:
                continue
            m = re.search(pat, low)
            if not m:
                continue
            prefix = name[:m.start()].strip(CLEAN)
            if len(prefix) < 3:                       # kein Gerätename davor -> Entitäts-ID als Quelle versuchen
                continue
            key = re.sub(r"\s+", " ", prefix.lower())
            g = groups.setdefault(key, {"name": prefix, "f": {}})
            # bei mehreren Treffern gewinnt der kürzere Name (genauer: „Notstromreserve“ vor „Notstrom Ladestand“)
            old = g["f"].get(field)
            if old is None or len(name) < len(old[1]):
                g["f"][field] = (eid, name)
            break                                         # eine Entität gehört zu genau einem Feld
    out = []
    conf = {c for c in configured if c}
    for key, g in groups.items():
        f = {k: v[0] for k, v in g["f"].items()}
        if "num" not in f and "dir" not in f:
            continue                                      # ohne Leistungssteuerung kein steuerbarer Speicher
        driver = "anker" if "num" in f and "dir" in f else "signed"
        out.append({"name": g["name"], "driver": driver, **{k: f.get(k, "") for k in ("num", "dir", "mode", "soc", "pv", "lim_res", "lim_dis", "lim_chg")},
                    "found": sorted(f), "configured": bool(f.get("num") in conf or f.get("dir") in conf)})
    out.sort(key=lambda u: u["name"].lower())
    return out


def find_grid(states, limit=6):
    """Mögliche Netz-Sensoren (Leistung in W oder kW, Name passt auf Netz/Zähler)."""
    out = []
    for eid, st in states.items():
        if not eid.startswith("sensor."):
            continue
        a = st.get("attributes") or {}
        unit = str(a.get("unit_of_measurement") or "")
        if unit not in ("W", "kW") or not _num(st.get("state")):
            continue
        name = _name(eid, st)
        if GRID_RE.search(name) or GRID_RE.search(eid):
            score = 2 if re.search(r"netz|grid", name + eid, re.I) else 1
            out.append((score, name.lower(), {"id": eid, "name": name, "state": st.get("state"), "unit": unit}))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [o[2] for o in out[:limit]]


def discover(states, cfg):
    cfgd = [u.get(k) for u in cfg.get("units", []) for k in ("num", "dir")]
    return {"units": find_units(states, cfgd), "grid": find_grid(states),
            "grid_set": bool((cfg.get("grid") or {}).get("entity"))}
