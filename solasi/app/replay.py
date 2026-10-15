"""Replay: simuliert die Regelung mit historischen Daten aus Home Assistant (Näherung)."""
import copy
import math
from datetime import datetime, timedelta, timezone

import drivers
from controller import decide

ALLOWED = {
    "control.min_gap": (1, 120), "control.threshold_on": (0, 1000), "control.threshold_off": (0, 1000),
    "control.offset_discharge": (0, 500), "control.offset_charge": (0, 500), "control.step": (1, 200),
    "control.total_max_dis": (0, 10000), "control.total_max_chg": (0, 10000), "control.split": ("equal", "soc", "sequential"),
    "features.eco": bool, "features.thresholds": bool, "features.ac_charge": bool, "features.strict_zero": bool,
    "soc.min": (0, 100), "soc.max": (0, 100), "soc.hyst": (0, 50), "soc.eco_threshold": (0, 100), "soc.base_load": (0, 5000),
}


def apply_overrides(cfg, overrides):
    out = copy.deepcopy(cfg)
    for path, val in (overrides or {}).items():
        rule = ALLOWED.get(path)
        if rule is None:
            raise ValueError(f"Einstellung nicht erlaubt: {path}")
        if rule is bool:
            val = bool(val)
        elif isinstance(rule, tuple) and isinstance(rule[0], str):
            if val not in rule:
                raise ValueError(f"{path}: ungültiger Wert")
        else:
            val = float(val)
            if not (rule[0] <= val <= rule[1]):
                raise ValueError(f"{path}: Wert außerhalb von {rule[0]} bis {rule[1]}")
        a, b = path.split(".")
        out[a][b] = val
    return out


def resample(history, t0, t1, step):
    """history: {entity: [(ts, state_str), ...]} -> {entity: [float|None]} auf festem Raster (Vorwärtsfüllung)."""
    n = int((t1 - t0) // step)
    out = {}
    for eid, pts in history.items():
        pts = sorted(pts)
        vals, j, cur = [], 0, None
        for k in range(n):
            t = t0 + k * step
            while j < len(pts) and pts[j][0] <= t:
                try:
                    v = float(pts[j][1])
                    cur = v if math.isfinite(v) else cur
                except (TypeError, ValueError):
                    pass            # unavailable/unknown: letzten Wert halten
                j += 1
            vals.append(cur)
        out[eid] = vals
    return out


def parse_history(raw):
    """Antwort von /api/history/period (minimal_response) in {entity: [(ts, state)]} umwandeln."""
    out = {}
    for series in raw or []:
        if not series:
            continue
        eid = series[0].get("entity_id")
        pts = []
        for p in series:
            ts = p.get("last_changed") or p.get("last_updated")
            if ts is None:
                continue
            try:
                t = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            pts.append((t, p.get("state")))
        if eid:
            out[eid] = pts
    return out


def needed_entities(cfg):
    ids = {"grid": cfg["grid"]["entity"], "extra": cfg["surplus"]["pv_x"], "house": cfg["surplus"]["house"]}
    units = []
    for u in cfg["units"]:
        if drivers.configured(u):
            units.append({"cfg": u, "soc": u["soc"], "rd": u["real_dis"], "rc": u["real_chg"], "pv": u["pv"],
                          "power": u.get("power", ""), "power_sign": u.get("power_sign", "discharge_positive"),
                          "basis": drivers.basis(u)})
    return ids, units


def check_requirements(cfg):
    ids, units = needed_entities(cfg)
    miss = []
    if not ids["grid"]:
        miss.append("Netzsensor")
    if not units:
        miss.append("mindestens ein Speicher")
    for u in units:
        n = u["cfg"]["name"]
        checks = [("soc", "Ladestand"), ("pv", "PV-Leistung")]
        if not u["power"]:
            checks += [("rd", "echte Entladeleistung"), ("rc", "echte Ladeleistung")]
        for key, label in checks:
            if not u[key]:
                miss.append(f"{n}: {label}")
    return miss


def build_data(cfg, hist_raw, t0, t1, step):
    ids, units = needed_entities(cfg)
    wanted = [e for e in [ids["grid"], ids["extra"], ids["house"]] if e]
    for u in units:
        wanted += [u[k] for k in ("soc", "rd", "rc", "pv", "power") if u[k]]
    series = resample(parse_history(hist_raw), t0, t1, step)
    n = int((t1 - t0) // step)

    def get(eid):
        s = series.get(eid) if eid else None
        return s if s is not None else [None] * n

    data = {"t0": t0, "step": step, "n": n, "grid": get(ids["grid"]), "extra": get(ids["extra"]) if ids["extra"] else None,
            "house": get(ids["house"]) if ids["house"] else None, "units": []}
    for u in units:
        pvs = get(u["pv"])
        if u["power"]:
            sign = 1 if u["power_sign"] == "discharge_positive" else -1
            net = [None if v is None else v * sign for v in get(u["power"])]
        else:
            d_, c_ = get(u["rd"]), get(u["rc"])
            net = [None if (a is None or b is None) else a - b for a, b in zip(d_, c_)]
        if u["basis"] == "battery":     # Batterie -> Abgabe ins Haus: ac = pv + batterie
            net = [None if (n is None or p_ is None) else p_ + n for n, p_ in zip(net, pvs)]
        rd = [None if n is None else max(n, 0.0) for n in net]
        rc = [None if n is None else max(-n, 0.0) for n in net]
        data["units"].append({"cfg": u["cfg"], "soc": get(u["soc"]), "rd": rd, "rc": rc, "pv": get(u["pv"])})
    # Beginn ohne vollständige Daten abschneiden
    first = 0
    for k in range(n):
        vals = [data["grid"][k]] + [x[key][k] for x in data["units"] for key in ("soc", "rd", "rc", "pv")]
        if all(v is not None for v in vals):
            first = k
            break
    else:
        raise ValueError("Keine vollständigen Verlaufsdaten gefunden (Recorder aktiv? Sensoren korrekt?)")
    for key in ("grid", "extra", "house"):
        if data[key] is not None:
            data[key] = data[key][first:]
    for x in data["units"]:
        for key in ("soc", "rd", "rc", "pv"):
            x[key] = x[key][first:]
    data["t0"] = t0 + first * step
    data["n"] = n - first
    return data


def _fill(seq, default=0.0):
    last = default
    out = []
    for v in seq:
        last = default if (v is None and last is None) else (last if v is None else v)
        out.append(last)
    return out


def simulate(cfg, data, tau=6.0, curtail=False, eff=0.95):
    """Schließt den Regelkreis mit einem einfachen Modell (Lastgang und PV aus der Historie)."""
    step, n = data["step"], data["n"]
    grid_h = _fill(data["grid"])
    extra = _fill(data["extra"]) if data["extra"] is not None else [0.0] * n
    units = data["units"]
    rd = [_fill(u["rd"]) for u in units]
    rc = [_fill(u["rc"]) for u in units]
    pv = [_fill(u["pv"]) for u in units]
    soc_h = [_fill(u["soc"], 50.0) for u in units]
    if data["house"] is not None:
        load = [max(h, 0.0) for h in _fill(data["house"])]
    else:
        load = [max(grid_h[k] + sum(rd[i][k] - rc[i][k] for i in range(len(units))) + extra[k], 0.0) for k in range(n)]

    soc = [soc_h[i][0] for i in range(len(units))]
    cap = [max(float(u["cfg"].get("capacity_kwh", 5.0)), 0.1) * 1000.0 for u in units]
    setv = [0.0] * len(units)
    out = [0.0] * len(units)
    alpha = 1 - math.exp(-step / tau)
    g_prev = grid_h[0]
    next_ctrl = 0.0
    m = {"imp": 0.0, "exp": 0.0, "writes": 0, "eco_s": 0.0, "min_soc": min(soc) if soc else 0.0, "curtailed": 0.0,
         "bat_dis": 0.0, "bat_chg": 0.0}
    g_series, soc_series = [], []
    stride = max(1, n // 300)
    for k in range(n):
        t = k * step
        if t >= next_ctrl:
            snap = {"meter_ok": True, "grid_w": g_prev, "units": [], "slots": [{"ent_state": None, "num_v": None, "pwr_w": None}] * 3,
                    "out_w": 0.0, "has_out": False, "pv_w": 0.0, "has_pv": False, "extra_pv": 0.0, "house_w": None, "custom_w": None}
            for i, u in enumerate(units):
                snap["units"].append({"cfg": u["cfg"], "k": u["cfg"]["name"], "has": True, "soc": soc[i], "set": setv[i],
                                      "real": abs(out[i]), "ac": out[i], "dir": "", "num_state": "0", "mode": None})
            d = decide(cfg, snap)
            for i, su in enumerate(snap["units"]):
                p = su["p"]
                if abs(p - setv[i]) >= cfg["control"]["step"] or (p == 0 and setv[i] != 0):
                    setv[i] = float(p)
                    m["writes"] += 1
            if d["eco_active"]:
                m["eco_s"] += max(cfg["control"]["min_gap"], step)
            next_ctrl = t + max(cfg["control"]["min_gap"], step)
        total_out = 0.0
        for i, u in enumerate(units):
            c = u["cfg"]
            s = setv[i]
            pvu = pv[i][k]
            if s >= 0:
                bat_ok = soc[i] > 5
                target = min(s, pvu + (c["max_dis"] if bat_ok else 0.0))
                if soc[i] >= 99 and pvu > s and not curtail:
                    target = pvu                      # Bypass: PV wird ungedrosselt durchgereicht
            else:
                chg = min(-s, c["max_chg"]) if soc[i] < 100 else 0.0
                target = -chg if soc[i] < 100 else pvu
            out[i] += (target - out[i]) * alpha
            bat = pvu - out[i]                         # + lädt, - entlädt
            if bat > 0 and soc[i] >= 100:
                m["curtailed"] += bat * step / 3600.0
                bat = 0.0
            if bat < 0 and soc[i] <= 5:
                bat = 0.0
            soc[i] = min(100.0, max(0.0, soc[i] + (bat * eff if bat > 0 else bat / eff) * step / 3600.0 / cap[i] * 100.0))
            if bat > 0:
                m["bat_chg"] += bat * step / 3600.0
            else:
                m["bat_dis"] += -bat * step / 3600.0
            total_out += out[i]
        g = load[k] - total_out - extra[k]
        g_prev = g
        m["imp"] += max(g, 0) * step / 3600.0
        m["exp"] += max(-g, 0) * step / 3600.0
        m["min_soc"] = min(m["min_soc"], min(soc))
        if k % stride == 0:
            g_series.append(round(g))
            soc_series.append(round(sum(soc) / len(soc), 1))
    res = {k: round(v, 1) if isinstance(v, float) else v for k, v in m.items()}
    res["imp"], res["exp"] = round(m["imp"] / 1000, 2), round(m["exp"] / 1000, 2)
    res["bat_dis"], res["bat_chg"] = round(m["bat_dis"] / 1000, 2), round(m["bat_chg"] / 1000, 2)
    res["curtailed"] = round(m["curtailed"] / 1000, 2)
    res["eco_h"] = round(m["eco_s"] / 3600, 1)
    res["end_soc"] = round(sum(soc) / len(soc), 1)
    res["series"] = {"grid": g_series, "soc": soc_series}
    return res


def actual_metrics(data):
    step = data["step"]
    g = _fill(data["grid"])
    imp = sum(max(x, 0) for x in g) * step / 3600 / 1000
    exp = sum(max(-x, 0) for x in g) * step / 3600 / 1000
    socs = [_fill(u["soc"], 50.0) for u in data["units"]]
    stride = max(1, data["n"] // 300)
    return {"imp": round(imp, 2), "exp": round(exp, 2),
            "end_soc": round(sum(s[-1] for s in socs) / len(socs), 1), "min_soc": round(min(min(s) for s in socs), 1),
            "series": {"grid": [round(v) for v in g[::stride]],
                       "soc": [round(sum(s[k] for s in socs) / len(socs), 1) for k in range(0, data["n"], stride)]}}


def hours_label(data):
    return round(data["n"] * data["step"] / 3600, 1)
