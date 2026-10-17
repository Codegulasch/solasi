"""Zusätzliche Zähler (Strom, Wasser, Gas …) aus Home-Assistant-Sensoren, mit Verbrauch seit Mitternacht."""
from datetime import datetime, timedelta

from util import load_json, now_local, save_json, snap_at

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
        # Tageswerte je Zähler für den Vergleich mit gestern: {Datum: {Entität: {"h": {Stunde: Wert}, "last": Wert}}}
        self.hist = raw.get("hist") or {}

    def _save(self):
        save_json(self.path, {"date": self.date, "base": self.base, "hist": self.hist})

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
                if day is not None:
                    dirty = self._note(today, eid, day) or dirty
            out.append({
                "entity": eid,
                "name": (it.get("name") or fname or eid).strip(),
                "value": val, "dec": dec, "unit": unit or "",
                "icon": it.get("icon") if it.get("icon") in ICONS else "zaehler",
                "color": it.get("color") if it.get("color") in COLORS else "zaehl",
                "day": day, "cmp": self.compare(today, eid) if day is not None else None,
            })
        if dirty:
            self._save()
        return out

    def _note(self, today, eid, day):
        """Merkt den Tageswert zu Beginn jeder Stunde und den letzten Stand. True, wenn etwas Neues gespeichert wurde."""
        rec = self.hist.setdefault(today, {}).setdefault(eid, {"h": {}, "last": day})
        h = str(now_local().hour)
        new = h not in rec["h"]
        if new:
            rec["h"][h] = day
        rec["last"] = day
        if len(self.hist) > 3:
            self.hist = {d: self.hist[d] for d in sorted(self.hist)[-3:]}
        return new

    def compare(self, today, eid):
        """Gestern: {"y": Tageswert bis zur gleichen Uhrzeit oder None, "full": ganzer Tag oder None}."""
        try:
            yd = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            return None
        rec = (self.hist.get(yd) or {}).get(eid)
        if not rec:
            return {"y": None, "full": None}
        now = now_local()
        y = snap_at(rec["h"], rec.get("last"), now.hour, now.minute)
        return {"y": None if y is None else round(y, 3), "full": rec.get("last")}
