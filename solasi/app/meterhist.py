"""Tagesverbrauch eines Zählers aus dem Verlauf von Home Assistant (für die Kachel-Statistik)."""
from datetime import datetime, timezone

from util import now_local


def _tz():
    return now_local().tzinfo or timezone.utc


def _local_date(ts):
    return datetime.fromtimestamp(ts, _tz()).strftime("%Y-%m-%d")


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def daily_from_stats(rows):
    """rows: [{start, change}] der Langzeitstatistik (stündlich) -> {datum: verbrauch}."""
    out = {}
    for r in rows or []:
        c = _f(r.get("change"))
        st = r.get("start")
        if c is None or st is None:
            continue
        ts = st / 1000.0 if isinstance(st, (int, float)) else datetime.fromisoformat(str(st).replace("Z", "+00:00")).timestamp()
        d = _local_date(ts)
        out[d] = out.get(d, 0.0) + max(c, 0.0)
    return out


def daily_from_history(points):
    """points: [(ts, state)] -> {datum: verbrauch} aus der Differenz der Tagesendstände.
    Zählerrückgänge (Tausch, Reset) zählen nicht negativ."""
    last = {}
    first = {}
    for ts, state in sorted(points or []):
        v = _f(state)
        if v is None:
            continue
        d = _local_date(ts)
        first.setdefault(d, v)
        last[d] = v
    out, prev = {}, None
    for d in sorted(last):
        base = prev if prev is not None else first[d]
        out[d] = max(last[d] - base, 0.0)
        prev = last[d]
    return out


def fill(daily, days):
    """Lückenlos die letzten `days` Tage (fehlende Tage = None), älteste zuerst."""
    from datetime import timedelta
    today = now_local().date()
    res = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        v = daily.get(d)
        res.append({"date": d, "value": None if v is None else round(v, 4)})
    return res
