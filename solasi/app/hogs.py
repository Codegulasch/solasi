"""Stromfresser: zeichnet die Leistung von Messsteckdosen auf und wertet sie aus.

Speicher (SQLite):
  raw    – alle ~10 s, 48 Stunden lang (für die feine Leistungskurve)
  minute – Minutenmittel, 90 Tage lang, mit lokaler Minute des Tages und Wochentag (für Filter nach Uhrzeit/Wochentag)
Die Reihe „_house“ ist der Gesamtverbrauch des Hauses; daraus ergibt sich der Rest „nicht gemessen“.
Aufgezeichnet wird ab dem Zeitpunkt, an dem ein Gerät eingerichtet ist – rückwirkend gibt es nichts.
"""
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from util import now_local

HOUSE = "_house"
RAW_KEEP = 48 * 3600
MIN_KEEP_DAYS = 90
MAX_DEVICES = 40
DEFAULT_ICON = "🔌"


def _tz():
    return now_local().tzinfo or timezone.utc


def clean_hogs(raw):
    """Geräteliste aus den Einstellungen bereinigen."""
    raw = raw if isinstance(raw, dict) else {}
    out, seen = [], set()
    for d in raw.get("devices") or []:
        if not isinstance(d, dict):
            continue
        power = str(d.get("power") or "").strip()[:120]
        name = str(d.get("name") or "").strip()[:40]
        if not power or not name:
            continue
        did = "".join(c for c in str(d.get("id") or name).lower() if c.isalnum() or c in "_-")[:30] or "dev"
        base, n = did, 2
        while did in seen or did == HOUSE:
            did = f"{base}{n}"
            n += 1
        seen.add(did)
        phase = d.get("phase")
        out.append({"id": did, "name": name, "icon": str(d.get("icon") or DEFAULT_ICON)[:4],
                    "power": power, "phase": phase if phase in ("L1", "L2", "L3") else ""})
        if len(out) >= MAX_DEVICES:
            break
    return {"devices": out}


def _watts(state, unit):
    try:
        v = float(state)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v * 1000.0 if str(unit or "").lower() == "kw" else v


class Hogs:
    def __init__(self, path, clock=time.time):
        self.clock = clock
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS raw(ts INTEGER, dev TEXT, w REAL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS raw_i ON raw(dev, ts)")
        self.db.execute("CREATE TABLE IF NOT EXISTS minute(ts INTEGER, dev TEXT, w REAL, mod INTEGER, wd INTEGER, day TEXT,"
                        " PRIMARY KEY(ts, dev))")
        self.db.execute("CREATE INDEX IF NOT EXISTS minute_d ON minute(day)")
        self.db.commit()
        self._buf = {}          # dev -> [Summe, Anzahl] der laufenden Minute
        self._buf_min = None
        self._last_clean = 0

    # ---------- Aufzeichnen ----------
    def sample(self, values, ts=None):
        """values: {dev: Watt oder None}. Wird etwa alle 10 s aufgerufen."""
        ts = int(self.clock() if ts is None else ts)
        m = ts // 60
        if self._buf_min is not None and m != self._buf_min:
            self._flush()
        self._buf_min = m
        rows = []
        for dev, w in values.items():
            if w is None:
                continue
            rows.append((ts, dev, float(w)))
            b = self._buf.setdefault(dev, [0.0, 0])
            b[0] += float(w)
            b[1] += 1
        if rows:
            self.db.executemany("INSERT INTO raw VALUES(?,?,?)", rows)
            self.db.commit()
        if ts - self._last_clean > 3600:
            self._last_clean = ts
            self.cleanup(ts)

    def _flush(self):
        if self._buf_min is None or not self._buf:
            self._buf = {}
            return
        ts = self._buf_min * 60
        dt = datetime.fromtimestamp(ts, _tz())
        mod, wd, day = dt.hour * 60 + dt.minute, dt.weekday(), dt.strftime("%Y-%m-%d")
        self.db.executemany("INSERT OR REPLACE INTO minute VALUES(?,?,?,?,?,?)",
                            [(ts, dev, s / n, mod, wd, day) for dev, (s, n) in self._buf.items() if n])
        self.db.commit()
        self._buf = {}

    def flush(self):
        self._flush()

    def cleanup(self, ts=None):
        ts = int(self.clock() if ts is None else ts)
        self.db.execute("DELETE FROM raw WHERE ts < ?", (ts - RAW_KEEP,))
        self.db.execute("DELETE FROM minute WHERE ts < ?", (ts - MIN_KEEP_DAYS * 86400,))
        self.db.commit()

    def remove_device(self, dev):
        self.db.execute("DELETE FROM raw WHERE dev=?", (dev,))
        self.db.execute("DELETE FROM minute WHERE dev=?", (dev,))
        self.db.commit()

    # ---------- Auswerten ----------
    @staticmethod
    def _where(days, tod_from, tod_to, weekdays, now=None):
        now = now or now_local()
        first = (now.date() - timedelta(days=max(int(days), 1) - 1)).strftime("%Y-%m-%d")
        w, args = ["day >= ?"], [first]
        if tod_from is not None and tod_to is not None and (tod_from, tod_to) not in ((0, 1440), (0, 0)):
            if tod_from < tod_to:
                w.append("mod >= ? AND mod < ?")
            else:                       # über Mitternacht, z. B. 22–6 Uhr
                w.append("(mod >= ? OR mod < ?)")
            args += [int(tod_from), int(tod_to)]
        if weekdays and len(set(weekdays)) < 7:
            w.append("wd IN (%s)" % ",".join("?" * len(weekdays)))
            args += [int(x) for x in weekdays]
        return " AND ".join(w), args

    def rank(self, devices, days=7, tod_from=None, tod_to=None, weekdays=None, price_ct=35.0, now=None):
        """-> Rangliste je Gerät (kWh, Anteil, €/Jahr, Standby) und Restverbrauch."""
        self._flush_if_due()
        where, args = self._where(days, tod_from, tod_to, weekdays, now)
        rows = self.db.execute(f"SELECT dev, w FROM minute WHERE {where}", args).fetchall()
        per = {}
        for dev, w in rows:
            per.setdefault(dev, []).append(w)
        house_w = per.get(HOUSE, [])
        minutes = len(house_w) or max((len(v) for v in per.values()), default=0)
        # Auf ein Jahr hochrechnen: kWh je gemessenem Zeitraum -> je 365 Tage
        scale = (365 * 1440.0 / minutes) if minutes else 0.0
        house_kwh = sum(house_w) / 60000.0
        out = []
        for d in devices:
            v = per.get(d["id"], [])
            kwh = sum(v) / 60000.0
            sv = sorted(v)
            standby = sv[int(len(sv) * 0.1)] if sv else None
            out.append({"id": d["id"], "name": d["name"], "icon": d.get("icon", DEFAULT_ICON), "phase": d.get("phase", ""),
                        "kwh": round(kwh, 3), "share": round(kwh / house_kwh * 100, 1) if house_kwh > 0 else None,
                        "eur_year": round(kwh * scale * price_ct / 100.0, 1), "kwh_year": round(kwh * scale, 1),
                        "standby_w": None if standby is None else round(standby, 1),
                        "avg_w": round(sum(v) / len(v), 1) if v else None,
                        "peak_w": round(max(v), 0) if v else None, "samples": len(v)})
        out.sort(key=lambda r: -r["kwh"])
        measured = sum(r["kwh"] for r in out)
        rest = max(house_kwh - measured, 0.0) if house_kwh > 0 else None
        return {"devices": out, "house_kwh": round(house_kwh, 3), "measured_kwh": round(measured, 3),
                "rest_kwh": None if rest is None else round(rest, 3),
                "rest_share": None if rest is None else round(rest / house_kwh * 100, 1),
                "rest_eur_year": None if rest is None else round(rest * scale * price_ct / 100.0, 1),
                "minutes": minutes, "days": days,
                "standby_w": round(sum(r["standby_w"] or 0 for r in out), 1),
                "standby_eur_year": round(sum((r["standby_w"] or 0) for r in out) * 8.76 * price_ct / 100.0, 1)}

    def _flush_if_due(self):
        if self._buf_min is not None and self._buf_min != int(self.clock()) // 60:
            self._flush()

    def curve(self, dev, day=None, res=60, now=None):
        """Leistungskurve eines Tages (lokaler Tag, „YYYY-MM-DD“, Standard heute).
        res: 10 (nur die letzten 48 h), 60 (Minute) oder 900 (Viertelstunde). -> [{t: Sekunde des Tages, w}]"""
        self._flush_if_due()
        now = now or now_local()
        day = day or now.strftime("%Y-%m-%d")
        d0 = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=_tz())
        t0 = int(d0.timestamp())
        t1 = int((d0 + timedelta(days=1)).timestamp())
        if res <= 10:
            rows = self.db.execute("SELECT ts, w FROM raw WHERE dev=? AND ts>=? AND ts<? ORDER BY ts", (dev, t0, t1)).fetchall()
            return [{"t": ts - t0, "w": round(w, 1)} for ts, w in rows]
        rows = self.db.execute("SELECT ts, w FROM minute WHERE dev=? AND ts>=? AND ts<? ORDER BY ts", (dev, t0, t1)).fetchall()
        if res <= 60:
            return [{"t": ts - t0, "w": round(w, 1)} for ts, w in rows]
        buckets = {}
        for ts, w in rows:
            b = (ts - t0) // res * res
            s = buckets.setdefault(b, [0.0, 0])
            s[0] += w
            s[1] += 1
        return [{"t": b, "w": round(s / n, 1)} for b, (s, n) in sorted(buckets.items())]

    def profile(self, dev, days=7, tod_from=None, tod_to=None, weekdays=None, now=None):
        """Durchschnittlicher Tagesverlauf (je Stunde) über die gewählten Tage -> 24 Werte in W (oder None)."""
        self._flush_if_due()
        where, args = self._where(days, tod_from, tod_to, weekdays, now)
        rows = self.db.execute(f"SELECT mod/60, AVG(w) FROM minute WHERE dev=? AND {where} GROUP BY mod/60", [dev] + args).fetchall()
        out = [None] * 24
        for h, w in rows:
            out[int(h)] = round(w, 1)
        return out

    def info(self):
        r = self.db.execute("SELECT MIN(ts), COUNT(*) FROM minute").fetchone()
        return {"since": r[0], "minutes": r[1]}
