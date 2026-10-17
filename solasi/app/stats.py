"""Tagesstatistik: integriert Leistungen zu Energie (Wh) und berechnet Kennzahlen."""
import time
from datetime import timedelta

from util import load_json, now_local, save_json, snap_at

KEYS = ("pv", "house", "imp", "exp", "bat_dis", "bat_chg")
KEEP_DAYS = 400
KEEP_HOURS = 3        # Tage mit Stundenständen (für den Vergleich mit gestern zur gleichen Uhrzeit)


class Stats:
    def __init__(self, path, clock=now_local):
        self.path = path
        self.clock = clock
        raw = load_json(path, {})
        self.days = raw.get("days", {})
        # Laufende Gesamtzähler (Wh) für das Energie-Dashboard: wachsen nur, auch wenn alte Tage gekürzt werden
        self.totals = {k: float(raw.get("totals", {}).get(k, sum(r.get(k, 0.0) for r in self.days.values())))
                       for k in KEYS}
        self.hours = raw.get("hours", {})       # {Datum: {Stunde: {Schlüssel: Wh}}}: Stand zu Beginn jeder Stunde
        self._last = None
        self._last_save = time.monotonic()

    def update(self, now_mono, pv_w, house_w, grid_w, bat_w):
        """Wird je Regelzyklus aufgerufen. Werte, die None sind, werden nicht gezählt."""
        if self._last is None:
            self._last = now_mono
            return
        dt = min(now_mono - self._last, 30.0)     # lange Lücken nicht hochrechnen
        self._last = now_mono
        if dt <= 0:
            return
        rec = self.days.setdefault(self.clock().strftime("%Y-%m-%d"), {**{k: 0.0 for k in KEYS}, "secs": 0.0})
        h = dt / 3600.0
        add = {"imp": max(grid_w, 0) * h, "exp": max(-grid_w, 0) * h}
        if pv_w is not None:
            add["pv"] = max(pv_w, 0) * h
        if house_w is not None:
            add["house"] = max(house_w, 0) * h
        if bat_w is not None:
            add["bat_dis"] = max(bat_w, 0) * h
            add["bat_chg"] = max(-bat_w, 0) * h
        for k, v in add.items():
            rec[k] += v
            self.totals[k] += v
        rec["secs"] += dt
        now = self.clock()
        hs = self.hours.setdefault(now.strftime("%Y-%m-%d"), {})
        if str(now.hour) not in hs:
            hs[str(now.hour)] = {k: round(rec[k], 3) for k in KEYS}
            if len(self.hours) > KEEP_HOURS:
                self.hours = {d: self.hours[d] for d in sorted(self.hours)[-KEEP_HOURS:]}
            self.save()
        if now_mono - self._last_save > 60:
            self.save()

    def save(self):
        keep = sorted(self.days)[-KEEP_DAYS:]
        self.days = {d: self.days[d] for d in keep}
        save_json(self.path, {"days": self.days, "totals": self.totals, "hours": self.hours})
        self._last_save = time.monotonic()

    def compare(self):
        """Gestern in kWh je Schlüssel: {"y": bis zur gleichen Uhrzeit oder None, "full": ganzer Tag oder None}."""
        now = self.clock()
        yd = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        rec, hs = self.days.get(yd), self.hours.get(yd) or {}
        out = {}
        for k in KEYS:
            full = None if not rec else rec.get(k, 0.0)
            y = snap_at({h: v.get(k) for h, v in hs.items() if v.get(k) is not None}, full, now.hour, now.minute)
            out[k] = {"y": None if y is None else round(y / 1000.0, 3), "full": None if full is None else round(full / 1000.0, 3)}
        return out

    @staticmethod
    def kpis(rec):
        kwh = {k: round(rec.get(k, 0.0) / 1000.0, 3) for k in KEYS}
        house, pv = kwh["house"], kwh["pv"]
        autarky = None if house <= 0 else max(0.0, min(1.0, 1 - kwh["imp"] / house))
        selfcons = None if pv <= 0 else max(0.0, min(1.0, (pv - kwh["exp"]) / pv))
        return {**kwh, "autarky": autarky, "selfcons": selfcons, "hours": round(rec.get("secs", 0) / 3600, 1)}

    def summary(self, days=30, prices=None):
        prices = prices or {"import_ct": 35.0, "feedin_ct": 8.0}
        out = []
        for day in sorted(self.days)[-days:]:
            k = self.kpis(self.days[day])
            k["date"] = day
            out.append(k)
        total = {key: round(sum(d[key] for d in out), 2) for key in KEYS}
        house = total["house"]
        total["autarky"] = None if house <= 0 else max(0.0, min(1.0, 1 - total["imp"] / house))
        total["selfcons"] = None if total["pv"] <= 0 else max(0.0, min(1.0, (total["pv"] - total["exp"]) / total["pv"]))
        covered = max(house - total["imp"], 0.0)            # selbst gedeckter Verbrauch
        total["saved_eur"] = round(covered * prices["import_ct"] / 100, 2)
        total["battery_eur"] = round(total["bat_dis"] * prices["import_ct"] / 100, 2)
        total["feedin_eur"] = round(total["exp"] * prices["feedin_ct"] / 100, 2)
        return {"days": out, "total": total}
