"""Automatik: Zeitpläne und Wenn-dann-Regeln, dazu der Wochenbericht.

Eine Regel: {id, name, enabled, when: {...}, then: {...}}
  when  time        at "HH:MM", days [0..6] (Mo=0)        -> einmal pro Tag zur angegebenen Minute
        soc_below   value (%)                           -> wenn der mittlere Ladestand darunter fällt
        soc_above   value (%)                           -> wenn er darüber steigt
        grid_above  value (W), minutes                  -> wenn der Netzbezug so lange darüber liegt
        pv_above    value (W)                           -> wenn die Solarleistung darüber steigt
  then  mode        mode (Modus-ID)                     -> Modus aktivieren
        notify      text                                -> Meldung senden
        charge      target (%), power_w (0 = max), units    -> Netz-Laden starten (Speicher aus dem Netz bis Ziel laden)
Bedingungen lösen nur beim Wechsel von „nicht erfüllt“ zu „erfüllt“ aus, nicht dauernd.
"""
import re

WHEN = ("time", "soc_below", "soc_above", "grid_above", "pv_above")
THEN = ("mode", "notify", "charge")
MAX_RULES = 30


def _num(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def clean_rules(raw):
    out, seen = [], set()
    for r in (raw if isinstance(raw, list) else [])[:MAX_RULES]:
        if not isinstance(r, dict):
            continue
        w, t = r.get("when") or {}, r.get("then") or {}
        kind, act = w.get("kind"), t.get("kind")
        if kind not in WHEN or act not in THEN:
            continue
        rid = re.sub(r"[^a-z0-9_-]", "", str(r.get("id") or "").lower())[:30] or f"r{len(out) + 1}"
        while rid in seen:
            rid += "x"
        seen.add(rid)
        when = {"kind": kind}
        if kind == "time":
            m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", str(w.get("at") or ""))
            when["at"] = f"{int(m.group(1)):02d}:{m.group(2)}" if m else "07:00"
            days = sorted({int(d) for d in (w.get("days") or []) if str(d).isdigit() and 0 <= int(d) <= 6})
            when["days"] = days or [0, 1, 2, 3, 4, 5, 6]
        elif kind in ("soc_below", "soc_above"):
            when["value"] = _num(w.get("value"), 0, 100, 20)
        elif kind == "grid_above":
            when["value"] = _num(w.get("value"), 0, 30000, 2000)
            when["minutes"] = _num(w.get("minutes"), 0, 120, 5)
        else:
            when["value"] = _num(w.get("value"), 0, 30000, 3000)
        then = {"kind": act}
        if act == "mode":
            then["mode"] = str(t.get("mode") or "")[:40]
        elif act == "charge":
            then["target"] = int(_num(t.get("target"), 1, 100, 20))
            then["power_w"] = int(_num(t.get("power_w"), 0, 20000, 0))
            then["units"] = [str(x)[:40] for x in (t.get("units") or []) if isinstance(x, str)][:8]
        else:
            then["text"] = str(t.get("text") or "")[:200]
        out.append({"id": rid, "name": str(r.get("name") or "Regel")[:60], "enabled": bool(r.get("enabled", True)),
                    "when": when, "then": then})
    return out


def describe(rule, modes=None):
    w, t = rule["when"], rule["then"]
    names = {m["id"]: m["name"] for m in (modes or [])}
    days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    if w["kind"] == "time":
        ds = "täglich" if len(w["days"]) == 7 else ", ".join(days[d] for d in w["days"])
        cond = f"{ds} um {w['at']} Uhr"
    elif w["kind"] == "soc_below":
        cond = f"der Ladestand unter {w['value']:.0f} % fällt"
    elif w["kind"] == "soc_above":
        cond = f"der Ladestand über {w['value']:.0f} % steigt"
    elif w["kind"] == "grid_above":
        cond = f"der Netzbezug {w['minutes']:.0f} Min. lang über {w['value']:.0f} W liegt"
    else:
        cond = f"die Solarleistung über {w['value']:.0f} W steigt"
    if t["kind"] == "mode":
        what = f"Modus „{names.get(t.get('mode'), t.get('mode'))}“ aktivieren"
    elif t["kind"] == "charge":
        what = f"Akkus bis {t['target']} % laden" + (f" ({t['power_w']} W)" if t.get("power_w") else "") + (
            " – " + ", ".join(t["units"]) if t.get("units") else "")
    else:
        what = f"melden: {t.get('text')}"
    if w["kind"] == "time":
        return f"{cond}: {what}"
    return f"Wenn {cond} → {what}"


def evaluate(rules, ctx, state):
    """ctx: {minute (0..1439), weekday, date, soc, grid_w, pv_w, now (Sekunden, monoton)}.
    state: wird verändert (merkt sich Zustände). -> Liste von Regeln, die jetzt auslösen."""
    fired = []
    for r in rules or []:
        if not r.get("enabled", True):
            continue
        w, rid = r["when"], r["id"]
        k = w["kind"]
        if k == "time":
            hh, mm = w["at"].split(":")
            if ctx["weekday"] in w["days"] and ctx["minute"] >= int(hh) * 60 + int(mm) and state.get(rid) != ctx["date"] \
                    and ctx["minute"] - (int(hh) * 60 + int(mm)) <= 10:       # nach langem Ausfall nicht nachholen
                state[rid] = ctx["date"]
                fired.append(r)
            continue
        if k == "soc_below":
            cond = ctx.get("soc") is not None and ctx["soc"] < w["value"]
        elif k == "soc_above":
            cond = ctx.get("soc") is not None and ctx["soc"] > w["value"]
        elif k == "grid_above":
            over = ctx.get("grid_w") is not None and ctx["grid_w"] > w["value"]
            key = rid + ":since"
            if over:
                state.setdefault(key, ctx["now"])
                cond = ctx["now"] - state[key] >= w["minutes"] * 60
            else:
                state.pop(key, None)
                cond = False
        else:
            cond = ctx.get("pv_w") is not None and ctx["pv_w"] > w["value"]
        was = state.get(rid, False)
        state[rid] = cond
        if cond and not was:
            fired.append(r)
    return fired


def weekly_report(summary, prices=None):
    """summary: Stats.summary(7). -> (Titel, Text)."""
    t, days = summary["total"], summary["days"]
    if not days:
        return "SOLASI Wochenbericht", "Für diese Woche liegen noch keine Daten vor."
    aut = "–" if t["autarky"] is None else f"{t['autarky'] * 100:.0f} %"
    best = max(days, key=lambda d: d["autarky"] or 0)
    lines = [f"Verbrauch {t['house']:.1f} kWh, Solar {t['pv']:.1f} kWh, Netzbezug {t['imp']:.1f} kWh.",
             f"Autarkie {aut}; der Speicher hat {t['bat_dis']:.1f} kWh abgegeben.",
             f"Ersparnis ca. {t['saved_eur']:.2f} €, Einspeisevergütung ca. {t['feedin_eur']:.2f} €."]
    if best.get("autarky") is not None:
        lines.append(f"Bester Tag: {best['date']} mit {best['autarky'] * 100:.0f} % Autarkie.")
    return "SOLASI Wochenbericht", "\n".join(lines)
