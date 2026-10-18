"""Netz-Laden: Speicher gezielt bis zu einem Ziel-Ladestand laden, auch aus dem Netz.

Ein Auftrag („Job“) nennt Ziel in %, Leistung (gesamt, 0 = so viel wie möglich), Speicher (leer = alle) und optional
die Reihenfolge. Die Verteilung ist reine Rechnung (alloc), das Zusammenspiel mit dem Regler steht in controller.decide.
"""
import time

ORDERS = ("low", "high", "list", "parallel")
ORDER_LABEL = {"low": "niedrigster Ladestand zuerst", "high": "höchster Ladestand zuerst",
               "list": "wie in der Speicherliste", "parallel": "alle gleichzeitig"}
MAX_HOURS = 24
EFFICIENCY = 0.9           # Wirkungsgrad für die Zeitschätzung (Netz → Batterie)


def _num(v, lo, hi, default):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if x != x or x in (float("inf"), float("-inf")):
        return default
    return min(max(x, lo), hi)


def clean_charge(raw):
    """Einstellungen: Standard-Reihenfolge und Gesamtleistung (0 = nur Grenzen der Speicher)."""
    raw = raw if isinstance(raw, dict) else {}
    order = raw.get("order")
    return {"order": order if order in ORDERS else "low", "max_w": int(_num(raw.get("max_w"), 0, 20000, 0))}


def _hold(raw):
    """Nach dem Ziel halten: none | until (Uhrzeit HH:MM) | manual (bis zur Freigabe)."""
    raw = raw if isinstance(raw, dict) else {}
    mode = raw.get("mode") if raw.get("mode") in ("until", "manual") else "none"
    at = str(raw.get("at") or "")
    ok = len(at) == 5 and at[2] == ":" and at[:2].isdigit() and at[3:].isdigit() and int(at[:2]) < 24 and int(at[3:]) < 60
    if mode == "until" and not ok:
        mode = "manual"
    return {"mode": mode, "at": at if ok else ""}


def clean_job(raw, names=None):
    """Auftrag prüfen. None, wenn ungültig."""
    if not isinstance(raw, dict):
        return None
    target = _num(raw.get("target"), 1, 100, None)
    if target is None:
        return None
    units = [str(x) for x in (raw.get("units") or []) if isinstance(x, str)]
    if names is not None:
        units = [x for x in units if x in names]
    order = raw.get("order")
    return {"target": int(round(target)), "power_w": int(_num(raw.get("power_w"), 0, 20000, 0)), "units": units,
            "order": order if order in ORDERS else "", "hours": _num(raw.get("hours"), 0.25, MAX_HOURS, MAX_HOURS),
            "started": raw.get("started") if isinstance(raw.get("started"), (int, float)) else time.time(),
            "start_soc": raw.get("start_soc") if isinstance(raw.get("start_soc"), dict) else {},
            "prev_lim": raw.get("prev_lim") if isinstance(raw.get("prev_lim"), dict) else {},
            "nodis": raw.get("nodis", True) is not False,
            "hold": _hold(raw.get("hold")),
            "source": str(raw.get("source") or "")[:60]}


def in_scope(job, units):
    """Speicher, die der Auftrag laden darf (nicht beobachtet, nicht pausiert, ladefähig)."""
    out = []
    for u in units:
        if u.get("obs") or u.get("paused"):
            continue
        if job["units"] and u["k"] not in job["units"]:
            continue
        out.append(u)
    return out


def alloc(cfg, job, units, caps=None):
    """-> {Speicher: Ladeleistung in W} (positiv). units: Snapshot-Speicher mit u["ccap_job"] (Leistungsgrenze)."""
    caps = caps or {}
    todo = [u for u in in_scope(job, units) if u["soc"] >= 0 and u["soc"] < job["target"] and u.get("ccap_job", 0) > 0]
    if not todo:
        return {}
    limits = {u["k"]: min(u["ccap_job"], caps.get(u["k"], float("inf"))) for u in todo}
    total = [x for x in (job["power_w"], cfg.get("charge", {}).get("max_w", 0)) if x and x > 0]
    left = float(min(total)) if total else float("inf")
    order = job["order"] or cfg.get("charge", {}).get("order", "low")
    if order == "low":
        todo.sort(key=lambda u: u["soc"])
    elif order == "high":
        todo.sort(key=lambda u: -u["soc"])
    out = {}
    if order == "parallel" and len(todo) > 1:
        # gleichmäßig, Überhang gedeckelter Speicher geht an die übrigen
        open_ = [u["k"] for u in todo if limits[u["k"]] > 0]
        left = min(left, sum(limits[k] for k in open_))
        while open_ and left > 1e-6:
            share = left / len(open_)
            capped = [k for k in open_ if limits[k] - out.get(k, 0.0) <= share]
            if not capped:
                for k in open_:
                    out[k] = out.get(k, 0.0) + share
                break
            for k in capped:
                add = limits[k] - out.get(k, 0.0)
                out[k] = limits[k]
                left -= add
            open_ = [k for k in open_ if k not in capped]
        return {k: v for k, v in out.items() if v > 0}
    for u in todo:
        if left <= 0:
            break
        a = min(limits[u["k"]], left)
        if a > 0:
            out[u["k"]] = a
            left -= a
    return out


def estimate(job, units, cfg, caps=None):
    """Benötigte Energie und grobe Dauer."""
    need, rows = 0.0, []
    for u in in_scope(job, units):
        if u["soc"] < 0:
            continue
        k = max(job["target"] - u["soc"], 0) / 100.0 * (u.get("cap") or 5.0)
        need += k
        rows.append({"name": u["k"], "soc": u["soc"], "kwh": round(k, 2)})
    cc = [dict(u, ccap_job=u.get("ccap_job", 0)) for u in units]
    al = alloc(cfg, job, cc, caps)
    # Dauer: Speicher laden nacheinander oder parallel – grob über die Gesamtleistung
    total = sum(al.values()) if al else 0.0
    order = job["order"] or cfg.get("charge", {}).get("order", "low")
    hours = None
    if need > 0 and total > 0:
        if order == "parallel":
            hours = max((r["kwh"] * 1000 / EFFICIENCY / max(al.get(r["name"], 0) or total, 1)) for r in rows)
        else:
            hours = need * 1000 / EFFICIENCY / total
    return {"kwh": round(need, 2), "hours": None if hours is None else round(hours, 2), "power_w": round(total), "rows": rows}


def headroom_caps(phases_view, units, fuse_a, margin=0.95):
    """Pro Speicher die Leistung, die seine Einspeise-Phase noch verträgt (W), sonst fehlt der Eintrag."""
    if not phases_view or not fuse_a:
        return {}
    loads = phases_view.get("loads") or {}
    out = {}
    for f in phases_view.get("feed_units") or []:
        ph = f.get("phase")
        if ph not in loads:
            continue
        u = next((x for x in units if x["k"] == f["name"]), None)
        own = abs(u["ac"]) / 230.0 if u and u.get("ac") is not None and u["ac"] < 0 else 0.0   # Laden steckt schon in der Last
        room_a = fuse_a * margin - (loads[ph] - own)
        out[f["name"]] = max(room_a, 0.0) * 230.0
    return out
