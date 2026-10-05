"""Lernt die nächtliche Grundlast des Hauses (Median je Nacht, Median der letzten Nächte)."""
import statistics
import time

from util import load_json, save_json

MIN_SAMPLES = 60       # mindestens eine Stunde Nachtdaten, damit die Nacht zählt
KEEP_NIGHTS = 14
USE_NIGHTS = 7


class BaseLoadLearner:
    def __init__(self, path):
        self.path = path
        d = load_json(path, {})
        self.nights = [float(x) for x in d.get("nights", [])][-KEEP_NIGHTS:]
        self.cur = [float(x) for x in d.get("cur", [])][-900:]
        self._last_minute = None
        self._last_save = time.monotonic()

    def observe(self, now_ts, house_w, night):
        """Pro Minute höchstens ein Messwert. Bei Nachtende wird die Nacht abgeschlossen."""
        if house_w is None:
            return
        if night:
            minute = int(now_ts // 60)
            if minute != self._last_minute:
                self._last_minute = minute
                self.cur.append(max(float(house_w), 0.0))
                self.cur = self.cur[-900:]
        elif self.cur:
            if len(self.cur) >= MIN_SAMPLES:
                self.nights.append(statistics.median(self.cur))
                self.nights = self.nights[-KEEP_NIGHTS:]
            self.cur = []
            self.save()
        if time.monotonic() - self._last_save > 300:
            self.save()

    @property
    def value(self):
        """Gelernte Grundlast in W (Median der letzten Nächte), vorläufig auch aus der laufenden Nacht."""
        if self.nights:
            return round(statistics.median(self.nights[-USE_NIGHTS:]))
        if len(self.cur) >= 30:
            return round(statistics.median(self.cur))
        return None

    def info(self):
        return {"value": self.value, "nights": [round(n) for n in self.nights], "tonight_samples": len(self.cur)}

    def save(self):
        save_json(self.path, {"nights": self.nights, "cur": self.cur})
        self._last_save = time.monotonic()


def is_night(pv_w, sun_state, utc_hour):
    """Nacht: PV-Leistung ~0, sonst Sonnenstand der HA-Entität sun.sun, sonst 1-5 Uhr."""
    if pv_w is not None:
        return pv_w < 20
    if sun_state in ("below_horizon", "above_horizon"):
        return sun_state == "below_horizon"
    return 1 <= utc_hour < 5
