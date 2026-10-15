"""Zusätzliche Zähler (Strom, Wasser, Gas …) aus Home-Assistant-Sensoren, mit Verbrauch seit Mitternacht."""
from util import load_json, save_json

ICONS = ("zaehler", "wasser", "blitz", "gas", "waerme", "haus", "sonne", "netz")
COLORS = ("zaehl", "water", "water2", "sun", "bat", "grid", "home", "accent")
MAX_ITEMS = 8


def _num(text):
    try:
        v = float(str(text).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _decimals(text):
    s = str(text)
    return min(len(s.split(".", 1)[1]), 3) if "." in s else 0


class Meters:
    def __init__(self, path):
        self.path = path
        raw = load_json(path, {})
        self.date = raw.get("date")
        self.base = {k: float(v) for k, v in (raw.get("base") or {}).items() if _num(v) is not None}

    def _save(self):
        save_json(self.path, {"date": self.date, "base": self.base})

    def compute(self, items, lookup, today):
        """items: Konfiguration; lookup(entity) -> (Zustand, Einheit, Name) oder None; today: Datum als Text."""
        dirty = False
        if self.date != today:                 # neuer Tag: Stand von Mitternacht (erster Wert des Tages) merken
            self.date, self.base, dirty = today, {}, True
        out = []
        for it in (items or [])[:MAX_ITEMS]:
            eid = (it.get("entity") or "").strip()
            if not eid:
                continue
            got = lookup(eid)
            raw, unit, fname = got if got else (None, "", "")
            val = _num(raw)
            dec = _decimals(raw) if val is not None else 0
            day = None
            if val is not None:
                if eid not in self.base or val < self.base[eid]:   # erster Wert oder Zähler zurückgesetzt/getauscht
                    self.base[eid], dirty = val, True
                day = round(val - self.base[eid], max(dec, 2)) if it.get("daily", True) else None
            out.append({
                "entity": eid,
                "name": (it.get("name") or fname or eid).strip(),
                "value": val, "dec": dec, "unit": unit or "",
                "icon": it.get("icon") if it.get("icon") in ICONS else "zaehler",
                "color": it.get("color") if it.get("color") in COLORS else "zaehl",
                "day": day,
            })
        if dirty:
            self._save()
        return out
