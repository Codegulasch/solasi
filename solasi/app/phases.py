"""Dreiphasiger Zähler: Leistung je Phase, Schieflast, Sicherungsauslastung und automatische Erkennung der Einspeise-Phase.

Erkennung (passiv, ohne etwas zu schalten): Jedes Mal, wenn sich die Ausgangsleistung der Speicher deutlich ändert, ändert
sich auf der Phase, in die sie einspeisen, die Netzleistung um genau das Gegenteil (mehr Einspeisung = weniger Bezug).
SOLASI summiert die Änderungen (Regression) je Phase; die Phase, die den Sprung am vollständigsten „sieht“, gewinnt.
Alte Messungen verlieren mit der Zeit an Gewicht. Eine manuell gesetzte Phase geht immer vor.
"""
from util import load_json, save_json

PH = ("L1", "L2", "L3")
STEP_MIN_W = 40          # kleinere Sprünge der Speicher-Leistung zählen nicht
MAX_GAP_S = 40           # Messungen weiter auseinander werden nicht verglichen
DECAY = 0.97             # Gewicht alter Sprünge je neuem Sprung
MIN_STEPS = 6            # so viele (gewichtete) Sprünge, bevor eine Phase genannt wird


def clean_phases(raw):
    raw = raw if isinstance(raw, dict) else {}
    out = {"enabled": bool(raw.get("enabled")), "invert": bool(raw.get("invert")),
           "feed": raw.get("feed") if raw.get("feed") in PH else "", "sensors": {}}
    try:
        out["fuse_a"] = max(0, min(125, int(raw.get("fuse_a") or 0)))
    except (TypeError, ValueError):
        out["fuse_a"] = 0
    try:
        out["warn_pct"] = max(50, min(100, int(raw.get("warn_pct") or 90)))
    except (TypeError, ValueError):
        out["warn_pct"] = 90
    s = raw.get("sensors") if isinstance(raw.get("sensors"), dict) else {}
    for p in PH:
        e = s.get(p) if isinstance(s.get(p), dict) else {}
        out["sensors"][p] = {k: str(e.get(k) or "").strip()[:120] for k in ("power", "voltage", "current")}
    return out


def _f(x, unit=None, kilo=False):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    if kilo and str(unit or "").lower() == "kw":
        v *= 1000.0
    return v


def read(cfg, ha):
    """Aktuelle Werte je Phase aus Home Assistant: {L1: {w, v, a}, …} (None, wo der Sensor fehlt)."""
    out = {}
    sign = -1.0 if cfg.get("invert") else 1.0
    for p in PH:
        s = cfg["sensors"][p]
        w = _f(ha.state(s["power"]), ha.attr(s["power"], "unit_of_measurement"), True) if s["power"] else None
        v = _f(ha.state(s["voltage"])) if s["voltage"] else None
        a = _f(ha.state(s["current"])) if s["current"] else None
        out[p] = {"w": None if w is None else w * sign, "v": v, "a": None if a is None else abs(a)}
    return out


def analyse(cfg, vals):
    """Schieflast und Sicherungsauslastung aus den Phasenwerten."""
    ws = {p: vals[p]["w"] for p in PH if vals[p]["w"] is not None}
    res = {"imbalance_w": None, "max_phase": None, "fuse": None}
    if len(ws) >= 2:
        hi = max(ws, key=lambda k: ws[k])
        res["imbalance_w"] = round(max(ws.values()) - min(ws.values()))
        res["max_phase"] = hi
    if cfg.get("fuse_a"):
        loads = {}
        for p in PH:
            a = vals[p]["a"]
            if a is None and vals[p]["w"] is not None:
                a = abs(vals[p]["w"]) / (vals[p]["v"] or 230.0)
            if a is not None:
                loads[p] = a
        if loads:
            ph = max(loads, key=lambda k: loads[k])
            pct = loads[ph] / cfg["fuse_a"] * 100
            res["fuse"] = {"phase": ph, "a": round(loads[ph], 1), "pct": round(pct), "warn": pct >= cfg.get("warn_pct", 90),
                           "loads": {k: round(v, 1) for k, v in loads.items()}}
    return res


class FeedDetector:
    def __init__(self, path=None):
        self.path = path
        self._load()
        self.prev = None
        self._dirty = 0

    def _load(self):
        raw = load_json(self.path, {}) if self.path else {}
        self.sxx = float(raw.get("sxx", 0.0))
        self.sxy = {p: float((raw.get("sxy") or {}).get(p, 0.0)) for p in PH}
        self.n = float(raw.get("n", 0.0))

    def reset(self):
        self.sxx, self.sxy, self.n, self.prev = 0.0, {p: 0.0 for p in PH}, 0.0, None
        self.save()

    def save(self):
        if self.path:
            save_json(self.path, {"sxx": self.sxx, "sxy": self.sxy, "n": self.n})

    def update(self, ts, out_w, vals):
        """out_w: Ausgangsleistung aller Speicher (W); vals: {L1: Watt|None, …} (Bezug positiv)."""
        if out_w is None or any(vals.get(p) is None for p in PH):
            self.prev = None
            return
        cur = (ts, float(out_w), {p: float(vals[p]) for p in PH})
        pr = self.prev
        self.prev = cur
        if not pr or cur[0] - pr[0] > MAX_GAP_S or cur[0] <= pr[0]:
            return
        dp = cur[1] - pr[1]
        if abs(dp) < STEP_MIN_W:
            return
        self.sxx = self.sxx * DECAY + dp * dp
        self.n = self.n * DECAY + 1
        for p in PH:
            self.sxy[p] = self.sxy[p] * DECAY + dp * (cur[2][p] - pr[2][p])
        self._dirty += 1
        if self._dirty >= 10:
            self._dirty = 0
            self.save()

    def result(self):
        """-> {phase, confidence (0–100), steps, slopes} – phase leer, solange nichts erkannt ist."""
        if self.sxx <= 0:
            return {"phase": "", "confidence": 0, "steps": round(self.n, 1), "slopes": {}}
        slope = {p: self.sxy[p] / self.sxx for p in PH}          # ideal: -1 auf der Einspeise-Phase, 0 auf den anderen
        a = {p: max(-s, 0.0) for p, s in slope.items()}
        tot = sum(a.values())
        best = max(a, key=lambda k: a[k])
        share = a[best] / tot if tot > 0 else 0.0
        conf = round(100 * share * min(1.0, self.n / 12.0) * min(1.0, a[best] / 0.6))
        ok = self.n >= MIN_STEPS and a[best] >= 0.4 and share >= 0.6
        return {"phase": best if ok else "", "confidence": conf if ok else min(conf, 49),
                "steps": round(self.n, 1), "slopes": {p: round(s, 2) for p, s in slope.items()}}


_PH_RE = {"L1": r"(?:phase[ _]?a\b|phase[ _]?1\b|\bl1\b|_a_|_1_|\ba_)", "L2": r"(?:phase[ _]?b\b|phase[ _]?2\b|\bl2\b|_b_|_2_|\bb_)",
          "L3": r"(?:phase[ _]?c\b|phase[ _]?3\b|\bl3\b|_c_|_3_|\bc_)"}


def discover(states):
    """Sensoren für Leistung (W), Spannung (V) und Strom (A) mit Vermutung zur Phase: [{entity, name, kind, phase, value}]."""
    import re
    out = []
    for eid, st in (states or {}).items():
        if not eid.startswith("sensor."):
            continue
        a = st.get("attributes") or {}
        unit, dc = a.get("unit_of_measurement"), a.get("device_class")
        kind = ("power" if dc == "power" or unit in ("W", "kW") else "voltage" if dc == "voltage" or unit == "V"
                else "current" if dc == "current" or unit == "A" else "")
        if not kind or eid.startswith("sensor.solasi_"):
            continue
        name = str(a.get("friendly_name") or eid)
        hay = (name + " " + eid.split(".", 1)[1]).lower()
        phase = next((p for p, rx in _PH_RE.items() if re.search(rx, hay)), "")
        # Gesamt-/Blindleistung u. Ä. nicht als Phasenwert vorschlagen
        if re.search(r"total|gesamt|reactive|blind|apparent|schein|factor|energy", hay):
            phase = ""
        out.append({"entity": eid, "name": name, "kind": kind, "phase": phase, "value": st.get("state"), "unit": unit or ""})
    out.sort(key=lambda x: (x["phase"] == "", x["name"].lower()))
    return out[:300]
