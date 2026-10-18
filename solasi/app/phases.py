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
    feed = raw.get("feed")
    if feed in PH:
        feed = {"*": feed}                                  # ältere Einstellung: gilt für alle Speicher
    feed = {str(k)[:60]: v for k, v in (feed.items() if isinstance(feed, dict) else []) if v in PH}
    out = {"enabled": bool(raw.get("enabled")), "invert": bool(raw.get("invert")), "feed": feed, "sensors": {}}
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
    loads = {}
    for p in PH:
        a = vals[p]["a"]
        if a is None and vals[p]["w"] is not None:
            a = abs(vals[p]["w"]) / (vals[p]["v"] or 230.0)
        if a is not None:
            loads[p] = round(a, 2)
    res["loads"] = loads
    if cfg.get("fuse_a") and loads:
        ph = max(loads, key=lambda k: loads[k])
        pct = loads[ph] / cfg["fuse_a"] * 100
        res["fuse"] = {"phase": ph, "a": round(loads[ph], 1), "pct": round(pct), "warn": pct >= cfg.get("warn_pct", 90),
                       "loads": {k: round(v, 1) for k, v in loads.items()}}
    return res


def _solve(A, B, lam):
    """Löst (A + lam·I)·x = B (kleines System, Gauß mit Pivotsuche)."""
    n = len(A)
    M = [[A[i][j] + (lam if i == j else 0.0) for j in range(n)] + [B[i]] for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return [0.0] * n
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


class FeedDetector:
    """Lernt je Speicher, auf welche Phase(n) er einspeist. Mehrere Speicher werden gemeinsam ausgewertet (Regression über
    alle Speicher-Leistungen), damit gleichzeitige Sprünge nicht verwechselt werden."""

    def __init__(self, path=None):
        self.path = path
        self.prev = None
        self._dirty = 0
        raw = load_json(path, {}) if path else {}
        try:
            self.names = [str(x) for x in raw.get("names", [])]
            self.sxx = {a: {b: float(v) for b, v in d.items()} for a, d in (raw.get("sxx") or {}).items()}
            self.sxy = {a: {p: float(v) for p, v in d.items()} for a, d in (raw.get("sxy") or {}).items()}
            self.nu = {a: float(v) for a, v in (raw.get("nu") or {}).items()}
            self.n = float(raw.get("n", 0.0))
        except (AttributeError, TypeError, ValueError):
            # Datei aus einer älteren Version (2.2.0 speicherte ein Gesamtergebnis) oder beschädigt: neu anfangen
            self.names, self.sxx, self.sxy, self.nu, self.n = [], {}, {}, {}, 0.0

    def reset(self):
        self.names, self.sxx, self.sxy, self.nu, self.n, self.prev = [], {}, {}, {}, 0.0, None
        self.save()

    def save(self):
        if self.path:
            save_json(self.path, {"names": self.names, "sxx": self.sxx, "sxy": self.sxy, "nu": self.nu, "n": self.n})

    def update(self, ts, outs, vals):
        """outs: {Speichername: Ausgangsleistung W}; vals: {L1: Watt|None, …} (Bezug positiv)."""
        outs = {k: float(v) for k, v in (outs or {}).items() if v is not None}
        if not outs or any(vals.get(p) is None for p in PH):
            self.prev = None
            return
        cur = (ts, outs, {p: float(vals[p]) for p in PH})
        pr = self.prev
        self.prev = cur
        if not pr or cur[0] - pr[0] > MAX_GAP_S or cur[0] <= pr[0]:
            return
        names = [k for k in outs if k in pr[1]]
        dx = {k: outs[k] - pr[1][k] for k in names}
        if not names or max(abs(v) for v in dx.values()) < STEP_MIN_W:
            return
        dph = {p: cur[2][p] - pr[2][p] for p in PH}
        for k in names:
            if k not in self.names:
                self.names.append(k)
        for a in self.names:
            self.sxx.setdefault(a, {})
            self.sxy.setdefault(a, {})
            for b in self.names:
                self.sxx[a][b] = self.sxx[a].get(b, 0.0) * DECAY
            for p in PH:
                self.sxy[a][p] = self.sxy[a].get(p, 0.0) * DECAY
            self.nu[a] = self.nu.get(a, 0.0) * DECAY
        for a in names:
            for b in names:
                self.sxx[a][b] = self.sxx[a].get(b, 0.0) + dx[a] * dx[b]
            for p in PH:
                self.sxy[a][p] = self.sxy[a].get(p, 0.0) + dx[a] * dph[p]
            if abs(dx[a]) >= STEP_MIN_W:
                self.nu[a] += 1
        self.n = self.n * DECAY + 1
        self._dirty += 1
        if self._dirty >= 10:
            self._dirty = 0
            self.save()

    def result(self):
        """-> {units: {name: {phase, confidence, share{L1,L2,L3}, steps}}, steps}; phase leer = noch nicht erkannt."""
        out = {}
        names = self.names
        if names:
            A = [[self.sxx.get(a, {}).get(b, 0.0) for b in names] for a in names]
            lam = 1.0 + 0.02 * sum(A[i][i] for i in range(len(names))) / max(len(names), 1)
            sol = {p: _solve(A, [self.sxy.get(a, {}).get(p, 0.0) for a in names], lam) for p in PH}
        for i, a in enumerate(names):
            c = {p: max(-sol[p][i], 0.0) for p in PH}            # Anteil der Leistung, der auf Phase p als weniger Bezug erscheint
            tot = sum(c.values())
            best = max(c, key=lambda k: c[k])
            share = c[best] / tot if tot > 0 else 0.0
            nu = self.nu.get(a, 0.0)
            conf = round(100 * share * min(1.0, nu / 12.0) * min(1.0, c[best] / 0.6))
            ok = nu >= MIN_STEPS and c[best] >= 0.4 and share >= 0.6
            out[a] = {"phase": best if ok else "", "confidence": conf if ok else min(conf, 49), "steps": round(nu, 1),
                      "share": {p: round(100 * c[p] / tot) if tot > 0 else 0 for p in PH}}
        return {"units": out, "steps": round(self.n, 1)}


def _rx(letter, num):
    # „Phase A“, „phase_a_power“, „Channel 1“, „L1“, „Kanal a“ …; Unterstrich zählt als Trenner
    return (r"(?<![a-z0-9])(?:phase|channel|kanal|ch|leg|l)[ _-]?(?:[%s]|%s)(?![a-z0-9])|(?<![a-z0-9])(?:%s)_(?:power|voltage|current)" % (letter, num, letter))


_PH_RE = {"L1": _rx("a", "1"), "L2": _rx("b", "2"), "L3": _rx("c", "3")}


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
