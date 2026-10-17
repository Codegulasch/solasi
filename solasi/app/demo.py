"""Demo-Modus: simulierte Werte für Oberfläche und Statistik, damit man SOLASI ohne Geräte ausprobieren kann.
Es wird nichts gesteuert und nichts an Home Assistant gesendet (der Regelzyklus ruht, solange Demo an ist)."""
import math
from datetime import datetime, timedelta


def _pv(h):
    """Solarleistung in W zur Tageszeit h (Stunden, dezimal) – Glocke zwischen 7 und 18 Uhr."""
    return max(0.0, 3200 * math.sin((h - 7) / 11 * math.pi)) if 7 <= h <= 18 else 0.0


def _house(h):
    return 380 + 140 * math.sin(h * 1.3) + (450 if 17.5 <= h <= 21 else 0) + (250 if 6.5 <= h <= 8 else 0)


def _step(h):
    """Ein Betriebszustand zur Tageszeit h -> (pv, house, bat_w) mit bat_w>0 = Entladen."""
    pv, house = _pv(h), _house(h)
    bat = house - pv                          # Überschuss lädt, Defizit entlädt
    bat = max(-2400.0, min(bat, 2400.0)) if (pv > 0 or h > 17) else 0.0
    return pv, house, bat


def status(cfg, now=None):
    now = now or datetime.now()
    h = now.hour + now.minute / 60
    pv, house, bat = _step(h)
    grid = max(house - pv - max(bat, 0), 0.0) if bat >= 0 else 0.0
    soc_a = max(8, min(100, 55 + 45 * math.sin((h - 12) / 24 * 2 * math.pi * 0.9)))
    soc_b = max(8, min(100, 40 + 30 * math.sin((h - 13) / 24 * 2 * math.pi * 0.9)))
    names = [u.get("name") or f"Speicher {i + 1}" for i, u in enumerate((cfg.get("units") or [])[:2])]
    while len(names) < 2:
        names.append(["Speicher A", "Speicher B"][len(names)])
    caps = [5.0, 10.0]
    share = [0.34, 0.66]
    units = []
    for i, (nm, soc) in enumerate(zip(names, (soc_a, soc_b))):
        b = round(bat * share[i])
        units.append({"name": nm, "pv": round(pv * share[i]), "soc": round(soc), "kwh": round(caps[i] * soc / 100, 1), "cap": caps[i],
                      "set": b, "real": abs(b), "plan": b, "bat": b, "full": soc >= 99, "available": True,
                      "dir": "discharge" if b > 20 else "charge" if b < -20 else "idle", "mode": "third_party_control"})
    ts = []
    for k in range(96):
        hh = (h - (95 - k) * 0.25) % 24
        p, ho, ba = _step(hh)
        ts.append((int(now.timestamp()) - (95 - k) * 900, round(p), round(ho), round(ba)))
    kwh = sum(u["kwh"] for u in units)
    day = {"house": round(0.65 * h + 1.5, 1), "pv": round(max(h - 7, 0) * 0.9, 1)}
    day["imp"] = round(day["house"] * 0.25, 1)
    day["bat"] = round(day["house"] * 0.3, 1)
    return {
        "connected": True, "enabled": True, "dry_run": False, "mode": "live", "demo": True,
        "safety": {"state": "active", "reason": "", "since": None}, "meter_ok": True,
        "pv_w": round(pv), "house_w": round(house), "battery_w": round(-bat), "bat_w": round(-bat), "grid_w": round(grid),
        "avg_soc": round((soc_a * 5 + soc_b * 10) / 15), "kwh": round(kwh, 1), "cap_kwh": 15, "target_w": round(max(bat, 0)), "t_target": round(max(bat, 0)),
        "flows": {"solar_house": round(min(pv, house)), "solar_battery": round(max(pv - house, 0)), "battery_house": round(max(bat, 0)), "grid_house": round(grid)},
        "units": units, "slots": [],
        "trend": {"t": [x[0] for x in ts], "pv": [x[1] for x in ts], "house": [x[2] for x in ts], "bat": [x[3] for x in ts]},
        "events": [{"ts": "18:32:10", "level": "act", "msg": f"{names[0]} voll – {names[1]} lädt 340 W aus dem Überschuss"},
                   {"ts": "14:02:11", "level": "info", "msg": "Demo: simulierte Werte, nichts wird gesteuert"},
                   {"ts": "09:41:00", "level": "info", "msg": "Modus „Ausgewogen“ aktiviert"}],
        "meter_view": {"items": [], "today": {**day, "cmp": {k: {"y": round(v * 0.9, 1), "full": round(v * 1.2, 1)} for k, v in day.items()}},
                       "show_day": True, "extra": False, "compare": "same", "order": []},
    }


def stats(today=None):
    today = today or datetime.now()
    days = []
    for i in range(14):
        d = today - timedelta(days=13 - i)
        pv = 3 + abs(math.sin(i / 2)) * 7
        house = 9 + math.sin(i) * 2
        imp = 1 + abs(math.cos(i)) * 2.5
        days.append({"date": d.strftime("%Y-%m-%d"), "pv": round(pv, 2), "house": round(house, 2), "imp": round(imp, 2), "exp": 0.3,
                     "bat_dis": round(2 + abs(math.sin(i)) * 2, 2), "bat_chg": 2.0, "autarky": round(1 - imp / house, 3),
                     "selfcons": round(1 - 0.3 / pv, 3)})
    tot = {k: round(sum(x[k] for x in days), 2) for k in ("pv", "house", "imp", "exp", "bat_dis", "bat_chg")}
    tot["autarky"] = round(1 - tot["imp"] / tot["house"], 3)
    tot["selfcons"] = round(1 - tot["exp"] / tot["pv"], 3)
    tot["saved_eur"] = round((tot["house"] - tot["imp"]) * 0.35, 2)
    tot["battery_eur"] = round(tot["bat_dis"] * 0.35, 2)
    tot["feedin_eur"] = round(tot["exp"] * 0.08, 2)
    return {"days": days, "total": tot}
