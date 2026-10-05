"""Tagesstatistik: integriert Leistungen zu Energie (Wh) und berechnet Kennzahlen."""
import time

from util import load_json, now_local, save_json

KEYS = ("pv", "house", "imp", "exp", "bat_dis", "bat_chg")
KEEP_DAYS = 400


class Stats:
    def __init__(self, path, clock=now_local):
        self.path = path
        self.clock = clock
        self.days = load_json(path, {}).get("days", {})
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
        if pv_w is not None:
            rec["pv"] += max(pv_w, 0) * h
        if house_w is not None:
            rec["house"] += max(house_w, 0) * h
        rec["imp"] += max(grid_w, 0) * h
        rec["exp"] += max(-grid_w, 0) * h
        if bat_w is not None:
            rec["bat_dis"] += max(bat_w, 0) * h
            rec["bat_chg"] += max(-bat_w, 0) * h
        rec["secs"] += dt
        if now_mono - self._last_save > 60:
            self.save()

    def save(self):
        keep = sorted(self.days)[-KEEP_DAYS:]
        self.days = {d: self.days[d] for d in keep}
        save_json(self.path, {"days": self.days})
        self._last_save = time.monotonic()

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
