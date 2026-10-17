"""Regelkern für 1-2 Anker SOLIX 4 E5000 Pro.

Die Entscheidungslogik (decide) ist eine reine Funktion ohne Seiteneffekte und wird
getrennt getestet. Controller liest Zustände, ruft decide() auf und schreibt die Ergebnisse.
"""
import asyncio
import collections
import copy
import json
import logging
import math
import os
import time
from datetime import datetime, timezone

import drivers
import energy
import watchdog
from ha import is_num, num
from learn import BaseLoadLearner, is_night
from meters import Meters
from mqtt import MqttBridge
from notify import Notifier
from stats import Stats
from util import data_path, load_json, now_local, save_json

log = logging.getLogger("solasi.ctrl")

# ----------------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------------


def default_unit(name):
    return {
        "name": name, "num": "", "dir": "", "soc": "", "mode": "",
        "real_dis": "", "real_chg": "", "pv": "", "max_dis": 800, "max_chg": 800, "capacity_kwh": 5.0,
        # Treiber: anker | signed | modal | limit | script (siehe drivers.py)
        "driver": "anker", "num_chg": "", "dir_dis": "", "dir_chg": "", "dir_stop": "", "mode_option": "",
        "enable": "", "script": "", "sign": "discharge_positive", "power": "", "power_sign": "discharge_positive",
        "can_charge": True, "curtail": True,
        "observe": False,    # nur beobachten: Werte lesen und anzeigen, aber nichts schreiben (z. B. wenn die Hersteller-App regelt)
        "power_basis": "",   # "" = automatisch, "ac" oder "battery" (siehe drivers.basis)
        "lim_dis": "",       # optional: Entität „Entladegrenze“ (% , vom Speicher). Wirksamer Mindest-Ladestand = der höhere Wert
        "lim_chg": "",       # optional: Entität „Ladeobergrenze“ (%). Darüber gilt der Speicher als voll
        # Rückfall beim Stoppen (Kill-Switch): Modus, den der Speicher dann bekommt (z. B. Eigenverbrauch)
        "fallback_mode": "", "fallback_value": "",
    }


def _pct(ha, eid):
    """Prozentwert aus einer Entität (0..100) oder None."""
    v = ha.state(eid) if eid else None
    if not is_num(v):
        return None
    x = float(v)
    return x if 0 <= x <= 100 else None


def default_slot(i, on_w, off_w, soc):
    return {
        "name": f"Verbraucher {i}", "ent": "", "num": "",
        "on_w": on_w, "on_delay": 2, "off_w": off_w, "off_delay": 3, "soc": soc,
        "min_on": 5, "min_off": 5, "cond": "",
        "unit_w": 1, "pmin": 0, "pmax": 2000, "pwr": "", "reserve": 0, "interval": 30,
        "block": False,
    }


DEFAULT_CONFIG = {
    "enabled": False,
    "dry_run": True,
    "grid": {"entity": "", "invert": False, "max_age": 60},
    "units": [default_unit("Speicher A"), default_unit("Speicher B")],
    "features": {"eco": True, "thresholds": True, "ac_charge": True,
                 "strict_zero": True, "failsafe": True, "pv_passthrough": True,
                 "enforce_mode": True},
    "control": {"min_gap": 5, "heartbeat": 10, "split": "soc",
                "total_max_dis": 800, "total_max_chg": 2000,
                "threshold_on": 120, "threshold_off": 80,
                "offset_discharge": 10, "offset_charge": 0, "step": 10},
    "soc": {"min": 15, "max": 99, "hyst": 5, "eco_threshold": 35, "base_load": 150,
            "learn_base_load": False, "base_load_margin": 10, "base_load_min": 50, "base_load_max": 600},
    "notify": {"service": "", "delay_min": 2, "cooldown_min": 60, "recovery": True,
               "events": {"meter": True, "offline": True, "empty": True, "curtail": True, "errors": True, "stopped": True}},
    "prices": {"import_ct": 35.0, "feedin_ct": 8.0},
    "meters": {"show_day": True, "extra": False, "items": [], "order": []},
    # Anordnung der Blöcke in Übersicht und Statistik (leer = Standardreihenfolge, gilt für alle Geräte)
    "ui": {"status_order": [], "status_hidden": [], "stats_order": [], "stats_hidden": []},
    "mqtt": {"enabled": True, "host": "", "port": 1883, "user": "", "password": "", "ssl": False, "prefix": "solasi"},
    "safety": {"kill_entity": "", "release_on_stop": True, "release_on_disable": True,
               "auto_meter_min": 5, "auto_errors": True, "resume_auto": False,
               "watchdog": True, "watchdog_min": 3},
    "names": {"mode_option": "third_party_control", "dis": "discharge", "chg": "charge"},
    "surplus": {
        "enabled": False, "dry_run": True, "source": "pv",
        "pv_x": "", "house": "", "custom": "",
        "slots": [default_slot(1, 300, 150, 95), default_slot(2, 600, 100, 95),
                  default_slot(3, 1000, 50, 98)],
    },
}


UI_BLOCKS = {
    "status": ["kpis", "meters", "hero", "trend", "units", "surplus", "log"],
    "stats": ["period", "tiles", "chart"],
}


def clean_order(raw):
    """Reihenfolge der Zählerkacheln: Schlüssel "day", "pv", "imp" oder "m:<entity>"; ohne Doppelte."""
    out = []
    for x in raw if isinstance(raw, list) else []:
        if isinstance(x, str) and 0 < len(x) <= 120 and x not in out:
            out.append(x)
    return out[:40]


def clean_ui(ui):
    """Nur bekannte Blöcke, keine Doppelten; ungültige Eingaben werden zu leeren Listen."""
    out = {}
    ui = ui if isinstance(ui, dict) else {}
    for kind, allowed in UI_BLOCKS.items():
        for suffix in ("order", "hidden"):
            raw = ui.get(f"{kind}_{suffix}")
            seen = []
            for x in raw if isinstance(raw, list) else []:
                if isinstance(x, str) and x in allowed and x not in seen:
                    seen.append(x)
            out[f"{kind}_{suffix}"] = seen
    return out


def deep_merge(base, over):
    """Ergänzt fehlende Schlüssel aus base; Listen werden elementweise ergänzt."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = {}
        for k, v in base.items():
            out[k] = deep_merge(v, over[k]) if k in over else copy.deepcopy(v)
        for k, v in over.items():
            if k not in base:
                out[k] = v
        return out
    if isinstance(base, list) and isinstance(over, list):
        out = []
        for i in range(max(len(base), len(over))):
            if i < len(base) and i < len(over):
                out.append(deep_merge(base[i], over[i]))
            elif i < len(over):
                out.append(over[i])
            else:
                out.append(copy.deepcopy(base[i]))
        return out
    return over


class ConfigStore:
    def __init__(self, path):
        self.path = path
        self.cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                self.cfg = deep_merge(DEFAULT_CONFIG, json.load(f))
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001
            log.error("Konfiguration unlesbar (%s) – Standardwerte", e)

    def save(self, new):
        merged = deep_merge(DEFAULT_CONFIG, new)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)
        self.cfg = merged


# ----------------------------------------------------------------------------
# Reine Entscheidungslogik
# ----------------------------------------------------------------------------


def _round_step(x, step):
    step = max(float(step), 1.0)
    return int(math.floor(x / step + 0.5) * step)


def cap_kwh(u):
    """Nutzbare Kapazität in kWh (Standard 5)."""
    try:
        v = float(u.get("capacity_kwh"))
    except (TypeError, ValueError):
        return 5.0
    return v if v > 0 else 5.0


def _ent_max(ha, eid):
    """Maximalwert einer number-Entität (Attribut „max“) oder None."""
    if not eid:
        return None
    m = ha.attr(eid, "max")
    return float(m) if isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0 else None


def _split(total, caps, weights):
    """Verteilt total (>0) auf höchstens zwei Geräte unter Beachtung der Limits."""
    if len(caps) == 1:
        return [min(total, caps[0])]
    wa, wb = weights
    w = wa + wb
    pa0 = total * wa / w if w > 0 else 0
    pa1 = min(pa0, caps[0])
    pb1 = min(total - pa1, caps[1])
    pa2 = min(total - pb1, caps[0])
    return [pa2, pb1]


def surplus_value(cfg, snap):
    """Überschuss in W (Verbraucher bereits im Hausverbrauch enthalten)."""
    sp = cfg["surplus"]
    src = sp["source"]
    if src == "custom" and snap.get("custom_w") is not None:
        return snap["custom_w"]
    haspv = snap["has_pv"] or snap["extra_pv"] > 0
    have_house = snap.get("house_w") is not None
    use_pv = src == "pv" and haspv and (have_house or snap["has_out"])
    if use_pv:
        house = max(snap["house_w"], 0) if have_house else max(
            snap["grid_w"] + snap["out_w"] + snap["extra_pv"], 0)
        return snap["pv_w"] + snap["extra_pv"] - house
    return -snap["grid_w"]


def slot_own_power(slot, snap_slot):
    """Geschätzte aktuelle Leistung eines Verbrauchers."""
    ent_state = snap_slot["ent_state"]
    if slot["ent"] and ent_state != "on":
        return 0.0
    if slot["pwr"] and snap_slot["pwr_w"] is not None:
        return snap_slot["pwr_w"]
    if slot["num"] and snap_slot["num_v"] is not None:
        return snap_slot["num_v"] * slot["unit_w"]
    if slot["ent"]:
        return float(slot["pmax"])
    return 0.0


def decide(cfg, snap):
    c, f, so = cfg["control"], cfg["features"], cfg["soc"]
    units = snap["units"]
    grid_w = snap["grid_w"]
    meter_ok = snap["meter_ok"]
    sp_on = cfg["surplus"]["enabled"]

    # ---- Verbraucher-Leistungen / Entladesperre ----
    slots = cfg["surplus"]["slots"]
    slot_own = [slot_own_power(s, snap["slots"][i]) for i, s in enumerate(slots)]
    blocked_w = sum(slot_own[i] for i, s in enumerate(slots) if s["block"]) if sp_on else 0.0

    set_total = sum(u["set"] for u in units if not u.get("obs"))   # beobachtete Speicher regelt jemand anders
    net_balance = grid_w + set_total
    net_dis = net_balance - blocked_w
    dis_now = set_total > 5
    chg_now = set_total < -5
    eff_on = c["threshold_on"] if f["thresholds"] else 1
    eff_off = c["threshold_off"] if f["thresholds"] else 1

    # ---- SOC-Logik je Gerät ----
    for u in units:
        soc, st = u["soc"], u["set"]
        ok = soc >= 0   # Verfügbarkeit der Leistungs-Entität ist hier egal: der Modus-Wächter macht sie verfügbar
        # Wirksame Grenzen: Die Grenzen im Speicher (Entladegrenze, Ladeobergrenze) kann SOLASI nicht überschreiben.
        lo = u.get("lim_dis")
        hi = u.get("lim_chg")
        u["min"] = max(so["min"], lo) if lo is not None else so["min"]
        u["max"] = min(so["max"], hi) if hi is not None else so["max"]
        u["full"] = ok and soc >= u["max"]
        u["elig_dis"] = ok and (soc > u["min"] if st > 5 else soc >= u["min"] + so["hyst"])
        u["elig_chg"] = bool(f["ac_charge"]) and drivers.can_charge(u["cfg"]) and ok and (
            soc < u["max"] if st < -5 else soc <= u["max"] - so["hyst"])
        # PV-Durchleitung: Der Speicher darf so viel ins Haus geben, wie seine Module gerade liefern, auch wenn die
        # Batterie unter dem Mindest-Ladestand ist. Die Batterie wird dadurch nicht entladen.
        pv_u = u.get("pv")
        pass_ok = bool(f.get("pv_passthrough", True)) and pv_u is not None
        u["pvcap"] = min(u["cfg"]["max_dis"], max(pv_u - 10.0, 0.0)) if pass_ok else 0.0
        u["dcap"] = u["cfg"]["max_dis"] if (u["elig_dis"] and not u.get("locked")) else u["pvcap"]
        u["ccap"] = u["cfg"]["max_chg"] if u["elig_chg"] else 0
        if u.get("obs"):
            u["dcap"] = u["ccap"] = u["pvcap"] = 0
        # Die Leistungs-Entität selbst begrenzt, was der Speicher annimmt (z. B. 800 W). Mehr zu verlangen bringt nichts,
        # der Rest muss vom anderen Speicher kommen.
        if u.get("nmax_dis"):
            u["dcap"] = min(u["dcap"], u["nmax_dis"])
        if u.get("nmax_chg"):
            u["ccap"] = min(u["ccap"], u["nmax_chg"])

    want_dis = any(u["dcap"] > 0 for u in units) and net_dis >= (eff_off if dis_now else eff_on)
    want_chg = any(u["elig_chg"] for u in units) and net_balance <= -(eff_off if chg_now else eff_on)

    socs = [u["soc"] for u in units if u["soc"] >= 0]
    known = [u for u in units if u["soc"] >= 0]
    cap_all = sum(u.get("cap") or 5.0 for u in known)
    avg_soc = (sum(u["soc"] * (u.get("cap") or 5.0) for u in known) / cap_all) if known else 100.0   # nach Kapazität gewichtet
    kwh_now = sum(max(0.0, min(100.0, u["soc"])) / 100.0 * (u.get("cap") or 5.0) for u in known)
    eco_active = bool(f["eco"]) and avg_soc <= so["eco_threshold"]

    # ---- Gesamtsollwert (positiv = Entladen) ----
    if want_dis:
        raw = max(net_dis - c["offset_discharge"], 0)
        cap = min(c["total_max_dis"], sum(u["dcap"] for u in units))
        if eco_active:
            # Eco begrenzt, was aus der Batterie kommt. Die Leistung der Module geht zusätzlich direkt ins Haus.
            cap = min(cap, (snap.get("base_load") or so["base_load"]) + sum(u["pvcap"] for u in units))
        t = min(raw, cap)
    elif want_chg:
        raw = max(abs(net_balance) - c["offset_charge"], 0)
        cap = min(c["total_max_chg"], sum(u["ccap"] for u in units))
        t = -min(raw, cap)
    else:
        t = 0

    # ---- Aufteilung ----
    plan = [0] * len(units)
    mode = c["split"]
    if t > 0:
        caps = [u["dcap"] for u in units]
        if mode == "sequential":
            a_first = units[0]["soc"] >= (units[1]["soc"] if len(units) > 1 else -1)
            w = [(1 if a_first else 0) if caps[0] > 0 else 0]
            if len(units) > 1:
                w.append((0 if a_first else 1) if caps[1] > 0 else 0)
        elif mode == "soc":
            w = [(max(u["soc"] - u["min"], 0) + 1) if caps[i] > 0 else 0 for i, u in enumerate(units)]
        else:
            w = [1 if caps[i] > 0 else 0 for i in range(len(units))]
        plan = _split(t, caps, w)
    elif t < 0:
        total = -t
        caps = [u["ccap"] for u in units]
        if mode == "sequential":
            a_first = units[0]["soc"] <= (units[1]["soc"] if len(units) > 1 else 101)
            w = [(1 if a_first else 0) if caps[0] > 0 else 0]
            if len(units) > 1:
                w.append((0 if a_first else 1) if caps[1] > 0 else 0)
        elif mode == "soc":
            w = [(max(u["max"] - u["soc"], 0) + 1) if caps[i] > 0 else 0 for i, u in enumerate(units)]
        else:
            w = [1 if caps[i] > 0 else 0 for i in range(len(units))]
        plan = [-p for p in _split(total, caps, w)]

    for i, u in enumerate(units):
        p = _round_step(plan[i], c["step"]) if meter_ok else 0
        u["p"] = p
        u["force"] = (bool(f["strict_zero"]) and drivers.curtail_enabled(u["cfg"])
                      and u["soc"] >= u["max"] and u["soc"] >= 0 and p == 0)

    surplus_w = surplus_value(cfg, snap) if sp_on else None
    return {
        "meter_ok": meter_ok, "grid_w": grid_w, "net_balance": net_balance, "net_dis": net_dis,
        "want_dis": want_dis, "want_chg": want_chg, "eco_active": eco_active,
        "avg_soc": avg_soc, "kwh": kwh_now, "cap_kwh": cap_all, "t_target": t, "blocked_w": blocked_w,
        "slot_own": slot_own, "surplus_w": surplus_w,
    }


# ----------------------------------------------------------------------------
# Controller (I/O)
# ----------------------------------------------------------------------------


class Controller:
    def __init__(self, ha, store):
        self.ha = ha
        self.store = store
        self.wake = asyncio.Event()
        self.events = collections.deque(maxlen=300)
        self.status = {}
        self._last_cycle = 0.0
        self._timers = {}  # (slot_idx, 'on'/'off') -> Startzeit
        self._prop_last = {}  # slot_idx -> Zeitpunkt der letzten Anpassung
        self._real_fix = {}  # Gerätename -> Zeitpunkt des letzten Real-Power-Fixes
        self._script_mem = {}  # Speicher mit Skript-Treiber -> zuletzt gesendeter Sollwert
        self.safety_path = data_path("safety.json")
        saved = load_json(self.safety_path, {})
        self.safety = {"state": saved.get("state", "active"), "reason": saved.get("reason", ""),
                       "since": saved.get("since"), "source": saved.get("source", "")}
        self._meter_bad_since = None
        self._clear_since = None
        self._wd_path = data_path("watchdog.json")
        self._wd_hash = load_json(self._wd_path, {}).get("hash", "")
        self.watchdog = {"state": "unbekannt", "detail": "Noch nicht abgeglichen", "json": "", "managed": False}
        self._hb_stopped = False
        self._mode_try = {}          # Speicher -> Zeitpunkt des letzten Versuchs, den Modus zu setzen
        self._releasing = False
        self._shutdown = False
        self.stats = Stats(data_path("stats.json"))
        self.learner = BaseLoadLearner(data_path("learn.json"))
        self.notifier = Notifier(self)
        self.curtail = {"state": "unbekannt", "since": None, "export_w": None, "note": "Noch nicht beurteilt"}
        self._curtail_bad = None
        self._curtail_good = None
        self._fail_times = []
        self._published = {}  # Entität -> zuletzt veröffentlichter Inhalt
        self._publish_failed = False
        self.card = {"installed": False, "target": "", "resource": "unbekannt",
                     "url": "", "base_url": "", "restart_needed": False}
        self.last_snap = None
        self.mqtt = MqttBridge(self, os.environ.get("SOLASI_VERSION", "dev"))
        self.meters = Meters(data_path("meters.json"))
        self._meters_at = 0.0
        self._meters_view = None
        self._trend_path = data_path("trend.json")
        self.trend = load_json(self._trend_path, {}).get("p", [])     # [Zeit, Solar, Haus, Speicher-Abgabe] alle 5 Minuten, 24 Stunden
        self.card_version = ""           # Version des Add-ons, die Karte vergleicht sie mit ihrer eigenen
        self.addon_slug = ""             # für „Antippen öffnet SOLASI“ in der Dashboard-Karte

    @property
    def cfg(self):
        return self.store.cfg

    # ---------- Hilfen ----------
    def event(self, level, msg):
        self.events.appendleft({"ts": time.strftime("%H:%M:%S"), "level": level, "msg": msg})
        log.log(logging.ERROR if level == "error" else logging.INFO, "%s", msg)

    def on_entity_event(self, eid):
        if eid == self.cfg["grid"]["entity"]:
            self.wake.set()

    async def act(self, dry, what, domain, service, data):
        """Führt einen Dienst aus oder protokolliert ihn im Testmodus."""
        if not self.cfg["enabled"]:
            return False
        if dry:
            self.event("test", f"Test: {what}")
            return False
        try:
            await self.ha.call_service(domain, service, data)
            self.event("act", what)
            return True
        except Exception as e:  # noqa: BLE001
            self._fail_times.append(time.monotonic())
            self.event("error", f"{what} fehlgeschlagen: {e}")
            return False

    # ---------- Zustand einlesen ----------
    def gather(self):
        cfg, ha = self.cfg, self.ha
        g = cfg["grid"]
        raw = ha.state(g["entity"]) if g["entity"] else None
        if cfg["features"]["failsafe"]:
            age = ha.age_seen(g["entity"]) if g["entity"] else float("inf")
            meter_ok = is_num(raw) and (g["max_age"] == 0 or age < g["max_age"])
        else:
            meter_ok = True
        grid_w = num(raw) * (-1 if g["invert"] else 1)
        names = cfg["names"]

        units, out_w, bat_w = [], 0.0, 0.0
        pv_w, pv_cfg, pv_known = 0.0, False, True
        out_cfg, out_known, bat_known = False, True, True
        for u in cfg["units"]:
            obs = bool(u.get("observe"))
            fl = drivers.flows(ha, u) if (drivers.configured(u) or u.get("pv") or obs) else None
            if u["pv"]:
                pv_cfg = True
                if fl["pv"] is None:
                    pv_known = False          # Sensor fehlt oder ist nicht verfügbar: unbekannt, nicht 0 W
                else:
                    pv_w += fl["pv"]
            if not drivers.configured(u) and not (obs and (u.get("soc") or u.get("pv"))):
                continue
            if obs:
                r = {"has": False, "set": 0.0, "dir": None, "num_state": None, "mode": None}
            else:
                r = drivers.read(ha, u, names, self._script_mem)
            if fl["has"]:
                out_cfg = True
                if fl["ac"] is None:
                    out_known = False
                else:
                    out_w += fl["ac"]
                if fl["bat"] is None:
                    bat_known = False
                else:
                    bat_w += fl["bat"]
            soc_s = ha.state(u["soc"]) if u["soc"] else None
            units.append({
                "cfg": u, "k": u["name"], "has": r["has"], "obs": obs,
                "cap": cap_kwh(u),
                "soc": num(soc_s, -1) if is_num(soc_s) else -1,
                "set": r["set"], "real": abs(fl["ac"]) if fl["ac"] is not None else 0.0,
                "pv": fl["pv"], "ac": fl["ac"], "bat": fl["bat"],
                "dir": r["dir"], "num_state": r["num_state"], "mode": r["mode"],
                "nmax_dis": _ent_max(ha, u["num"]), "nmax_chg": _ent_max(ha, u.get("num_chg") or u["num"]),
                "lim_dis": _pct(ha, u.get("lim_dis")), "lim_chg": _pct(ha, u.get("lim_chg")), "locked": False,
            })
        self._update_locks(units)
        has_pv = pv_cfg and pv_known
        has_out = out_cfg and out_known
        bat_total = bat_w if (out_cfg and bat_known) else None

        sp = cfg["surplus"]
        extra = num(ha.state(sp["pv_x"])) if sp["pv_x"] else 0.0
        hs0 = ha.state(sp["house"]) if sp["house"] else None
        house_gross = num(hs0) if is_num(hs0) else (max(grid_w + out_w + extra, 0.0) if has_out else None)
        slots = []
        for s in sp["slots"]:
            n_s = ha.state(s["num"]) if s["num"] else None
            p_s = ha.state(s["pwr"]) if s["pwr"] else None
            slots.append({
                "ent_state": ha.state(s["ent"]) if s["ent"] else None,
                "num_v": num(n_s) if is_num(n_s) else None,
                "pwr_w": num(p_s) if is_num(p_s) else None,
            })
        hs = ha.state(sp["house"]) if sp["house"] else None
        cs = ha.state(sp["custom"]) if sp["custom"] else None
        return {
            "meter_ok": meter_ok, "grid_w": grid_w, "units": units, "slots": slots,
            "out_w": out_w, "has_out": has_out, "pv_w": pv_w, "has_pv": has_pv, "bat_w": bat_total,
            "pv_configured": pv_cfg,
            "extra_pv": extra,
            "house_w": num(hs) if is_num(hs) else None,
            "custom_w": num(cs) if is_num(cs) else None,
            "house_gross": house_gross,
            "sun": ha.state("sun.sun"),
            "base_load": self.base_load_effective(),
        }

    # ---------- Speicher, der trotz Sollwert nichts liefert ----------
    LOCK_AFTER_S = 90          # so lange Sollwert > 0 und keine Abgabe, bis der Speicher als gesperrt gilt
    LOCK_RETRY_S = 1200        # nach dieser Zeit wird es erneut versucht
    LOCK_SOC_STEP = 3          # oder wenn der Ladestand um so viel gestiegen ist

    def _update_locks(self, units):
        """Erkennt Speicher, die eine Abgabe angefordert bekommen, aber nichts liefern (z. B. Entladegrenze in der
        Hersteller-App). Solche Speicher bekommen keinen Anteil mehr, bis sich etwas ändert."""
        cfg = self.cfg
        lk = getattr(self, "_locks", None)
        if lk is None:
            lk = self._locks = {}
        now = time.monotonic()
        live = bool(cfg["enabled"]) and not cfg["dry_run"] and not self.stopped
        for u in units:
            st = lk.setdefault(u["k"], {"bad": None, "at": None, "soc": None})
            if u.get("obs") or not live or not u["has"]:
                st["bad"] = st["at"] = None
                continue
            if st["at"] is not None:
                if u["soc"] >= (st["soc"] if st["soc"] is not None else 0) + self.LOCK_SOC_STEP or now - st["at"] > self.LOCK_RETRY_S:
                    st["at"] = st["bad"] = None
                    self.event("info", f"{u['k']}: wird wieder angefragt")
            else:
                real = u.get("ac")
                bad = u["set"] > 30 and real is not None and abs(real) < 10 and u["soc"] >= 0
                if not bad:
                    st["bad"] = None
                else:
                    st["bad"] = st["bad"] or now
                    if now - st["bad"] >= self.LOCK_AFTER_S:
                        st["at"], st["soc"] = now, u["soc"]
                        self.event("info", f"{u['k']}: liefert trotz {u['set']:.0f} W Sollwert nichts (bei {u['soc']:.0f} %). "
                                           "Vermutlich greift die Entladegrenze im Speicher. Er bekommt vorerst keinen Anteil.")
            u["locked"] = st["at"] is not None

    # ---------- Hauptschleifen ----------
    async def run(self):
        await asyncio.gather(self._control_loop(), self._surplus_loop(), self._heartbeat_loop())

    async def _control_loop(self):
        while True:
            c = self.cfg["control"]
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=c["heartbeat"])
            except asyncio.TimeoutError:
                pass
            self.wake.clear()
            wait = c["min_gap"] - (time.monotonic() - self._last_cycle)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_cycle = time.monotonic()
            if not self.ha.connected:
                continue
            try:
                await self.cycle()
            except Exception:  # noqa: BLE001
                log.exception("Fehler im Regelzyklus")
                self.event("error", "Fehler im Regelzyklus (siehe Add-on-Protokoll)")

    async def _surplus_loop(self):
        while True:
            await asyncio.sleep(2)
            if (not self.ha.connected or not self.cfg["surplus"]["enabled"] or self.stopped or self._releasing
                    or self._shutdown):
                self._timers.clear()
                continue
            try:
                await self.surplus_cycle()
            except Exception:  # noqa: BLE001
                log.exception("Fehler in der Überschusssteuerung")
                self.event("error", "Fehler in der Überschusssteuerung (siehe Add-on-Protokoll)")

    # ---------- Regelzyklus ----------
    async def cycle(self):
        cfg = self.cfg
        snap = self.gather()
        self.last_snap = snap
        d = decide(cfg, snap)
        dry = cfg["dry_run"]
        await self._safety_check(snap, d)
        # Speicher gleichzeitig ansteuern: ein hängender Speicher soll die anderen nicht aufhalten
        todo = [] if (self.stopped or self._releasing or self._shutdown) else snap["units"]
        results = await asyncio.gather(*(self._apply_unit(u, d, dry) for u in todo), return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.error("Fehler beim Ansteuern eines Speichers: %r", r)
                self.event("error", f"Fehler beim Ansteuern eines Speichers: {r}")
        self._after_cycle(snap, d)
        self._publish(snap, d)
        await self.publish_entities()
        await self.notifier.check(self._problems(snap, d))

    async def _apply_unit(self, u, d, dry):
        """Setzt den berechneten Sollwert über den Treiber des Speichers um."""
        cfg = self.cfg
        names, f, c = cfg["names"], cfg["features"], cfg["control"]
        uc = u["cfg"]
        p = u["p"]
        if u.get("obs"):
            return                                   # beobachtet: nichts schreiben

        # 1) Voraussetzungen schaffen (Fernsteuerung einschalten, Arbeitsmodus auf externe Steuerung setzen).
        #    Mit „Modus automatisch setzen“ passiert das sofort beim Start, nach „Fortsetzen“ und wenn der Modus von außen
        #    verstellt wird, nicht erst, wenn ein Sollwert anliegt. Dann höchstens alle mode_retry_s Sekunden.
        needed = p != 0 or u["force"]
        if d["meter_ok"] and (needed or f.get("enforce_mode", True)):
            cmds = drivers.guard_commands(uc, names, self.ha)
            now_g = time.monotonic()
            if cmds and (needed or now_g - self._mode_try.get(u["k"], -1e9) >= self.mode_retry_s):
                self._mode_try[u["k"]] = now_g
                did = False
                for dom, svc, data, what in cmds:
                    did = await self.act(dry, what, dom, svc, data) or did
                if did and uc.get("num"):
                    for _ in range(20):                   # Entität wird oft erst im Zielmodus verfügbar
                        if is_num(self.ha.state(uc["num"])):
                            break
                        await asyncio.sleep(0.5)

        # 2) Sollwert schreiben
        s = drivers.read(self.ha, uc, names, self._script_mem)
        now = time.monotonic()
        # Real-Power-Check: 0 W erneut senden, wenn der echte Sensor noch Leistung zeigt – höchstens 1x pro Minute
        real_fix = (f["failsafe"] and p == 0 and u["real"] > 10
                    and now - self._real_fix.get(u["k"], -1e9) >= 60)
        need = (dry or s["has"]) and drivers.needs_write(uc, s, p, u["force"], c["step"], real_fix, names)
        if not need:
            return
        if real_fix:
            self._real_fix[u["k"]] = now
        if dry:
            await self.act(True, f"{u['k']}: {s['set']:.0f} W → {p} W ({drivers.label(p, u['force'])}); "
                                 f"Netz {d['grid_w']:.0f} W, Bilanz {d['net_balance']:.0f} W", "", "", {})
            return
        for dom, svc, data, what in drivers.commands(uc, s, p, u["force"], names, self.ha):
            await self.act(False, what + (f"; Netz {d['grid_w']:.0f} W" if data.get("entity_id") == uc.get("num") else ""),
                           dom, svc, data)
        if drivers.driver(uc) == "script":
            self._script_mem[u["k"]] = float(p)

    # ---------- Überschuss ----------
    async def surplus_cycle(self):
        cfg = self.cfg
        snap = self.gather()
        d = decide(cfg, snap)
        sp = cfg["surplus"]
        dry = sp["dry_run"]
        now = time.monotonic()
        surplus = d["surplus_w"]
        avg = 100.0 if self.curtail["state"] == "fehlgeschlagen" else d["avg_soc"]   # Abregelung greift nicht: Verbraucher dürfen früher laufen

        for i, s in enumerate(sp["slots"]):
            slot_snap = snap["slots"][i]
            cond_ok = (not s["cond"]) or self.ha.state(s["cond"]) == "on"

            # --- Ein-/Ausschalten (nur mit Schalter) ---
            if s["ent"]:
                st = slot_snap["ent_state"]
                on_true = (d["meter_ok"] and st == "off" and surplus > s["on_w"] and avg >= s["soc"])
                off_true = (st == "on" and (surplus < -s["off_w"] or avg < s["soc"] - 5))
                for kind, cond in (("on", on_true), ("off", off_true)):
                    key = (i, kind)
                    if not cond:
                        self._timers.pop(key, None)
                        continue
                    since = self._timers.setdefault(key, now)
                    delay = (s["on_delay"] if kind == "on" else s["off_delay"]) * 60
                    gap = (s["min_off"] if kind == "on" else s["min_on"]) * 60
                    if now - since >= delay and self.ha.age_changed(s["ent"]) >= gap and (kind == "off" or cond_ok):
                        self._timers.pop(key, None)
                        svc = "turn_on" if kind == "on" else "turn_off"
                        txt = "einschalten" if kind == "on" else "ausschalten"
                        await self.act(dry, f"{s['name']}: {txt} (Überschuss {surplus:.0f} W)",
                                       "homeassistant", svc, {"entity_id": s["ent"]})

            # --- Stufenlose Regelung ---
            if s["num"]:
                await self._prop_control(i, s, slot_snap, d, dry, cond_ok, now)

    async def _prop_control(self, i, s, slot_snap, d, dry, cond_ok, now):
        if not (d["meter_ok"] and slot_snap["num_v"] is not None and d["avg_soc"] >= s["soc"]
                and cond_ok and (not s["ent"] or slot_snap["ent_state"] == "on")):
            return
        if now - self._prop_last.get(i, -1e9) < s["interval"]:
            return
        own = d["slot_own"][i]
        free = d["surplus_w"] + own - s["reserve"]
        f_w = min(free, s["pmax"])
        if s["ent"]:
            tgt = max(f_w, s["pmin"])
        elif own < 1 and f_w < max(s["on_w"], s["pmin"]):
            tgt = 0
        elif f_w < s["pmin"]:
            tgt = 0
        else:
            tgt = f_w
        step = num(self.ha.attr(s["num"], "step"), 1) or 1
        vmin = num(self.ha.attr(s["num"], "min"), 0)
        vmax = num(self.ha.attr(s["num"], "max"), 1e6)
        raw = tgt / max(s["unit_w"], 0.01)
        new_v = min(max(math.floor(raw / step) * step, vmin), vmax)
        new_v = round(new_v, 2)
        cur = slot_snap["num_v"]
        if abs(new_v - cur) < step:
            return
        self._prop_last[i] = now
        await self.act(dry, f"{s['name']}: Vorgabe {cur:g} → {new_v:g} (Ziel {tgt:.0f} W, "
                            f"Überschuss {d['surplus_w']:.0f} W, eigene Leistung {own:.0f} W)",
                       "number", "set_value", {"entity_id": s["num"], "value": new_v})

    async def apply_settings(self, changes, source="Oberfläche"):
        """Ändert Einstellungen (z. B. Regelung ein/aus) und führt die Folgen aus – für Oberfläche und MQTT."""
        cfg = self.cfg
        new = copy.deepcopy(cfg)
        new.update(changes)
        await self.save_config(new)
        self.event("info", f"{source}: " + ", ".join(f"{k} = {v}" for k, v in changes.items()))

    async def save_config(self, data):
        was_live = bool(self.cfg["enabled"]) and not self.cfg["dry_run"]
        if isinstance(data, dict) and "ui" in data:
            data = {**data, "ui": clean_ui(data["ui"])}
        if isinstance(data, dict) and isinstance(data.get("meters"), dict):
            data = {**data, "meters": {**data["meters"], "order": clean_order(data["meters"].get("order"))}}
        self.store.save(data)
        self._meters_view = None             # geänderte Zähler sofort neu lesen
        now_live = bool(self.cfg["enabled"]) and not self.cfg["dry_run"]
        if now_live and not was_live:
            self._mode_try.clear()           # Live-Steuerung eingeschaltet: Modus sofort setzen
        if was_live and not now_live and self.cfg["safety"]["release_on_disable"] and not self.stopped:
            self.event("info", "Live-Steuerung beendet: Speicher werden freigegeben")
            asyncio.create_task(self.release_all("Steuerung ausgeschaltet", force=True))
        self.wake.set()
        if self.ha.connected:
            asyncio.create_task(self.sync_watchdog())
        if self.status:
            self.status["enabled"], self.status["dry_run"] = self.cfg["enabled"], self.cfg["dry_run"]
        await self.publish_entities()

    # ---------- Kill-Switch / Sicherheit ----------
    @property
    def stopped(self):
        return self.safety["state"] == "stopped"

    def _save_safety(self):
        save_json(self.safety_path, self.safety)

    async def kill(self, reason, source="manual"):
        """Stoppt die Steuerung und gibt die Speicher frei (Rückfall-Modus). Wiederholtes Auslösen ist harmlos."""
        if self.stopped:
            return False
        cfg = self.cfg
        live = bool(cfg["enabled"]) and not cfg["dry_run"]
        self.safety = {"state": "stopped", "reason": reason, "since": time.strftime("%d.%m. %H:%M:%S"), "source": source}
        self._save_safety()
        self.event("error", f"⛔ SOLASI gestoppt: {reason}")
        if cfg["safety"]["release_on_stop"] and live:
            await self.release_all("Stopp")
        elif live:
            self.event("info", "Speicher bleiben im aktuellen Zustand (Freigabe beim Stoppen ist ausgeschaltet)")
        if cfg["notify"]["events"].get("stopped", True):
            await self.notifier.send("⛔ SOLASI gestoppt", f"{reason}. Die Speicher wurden "
                                     + ("freigegeben." if (cfg["safety"]["release_on_stop"] and live) else "nicht verändert."), "stopped")
        self._publish_stopped()
        return True

    def resume(self):
        if not self.stopped:
            return False
        self.safety = {"state": "active", "reason": "", "since": None, "source": ""}
        self._save_safety()
        self._meter_bad_since = None
        self._clear_since = None
        self._fail_times.clear()
        self._mode_try.clear()               # Modus sofort wieder auf externe Steuerung setzen, ohne Sperrzeit
        self.event("info", "▶ SOLASI läuft wieder")
        self.wake.set()
        return True

    def _publish_stopped(self):
        if self.status:
            self.status["safety"] = dict(self.safety)

    async def release_all(self, why, force=False):
        """Gibt alle Speicher an ihr eigenes Regelverhalten zurück und prüft das Ergebnis."""
        cfg, ha = self.cfg, self.ha
        if self._releasing:
            return
        if not force and (not cfg["enabled"] or cfg["dry_run"]):
            self.event("info", "Test/aus: keine Freigabe nötig")
            return
        self._releasing = True
        try:
            checks = []
            for uc in cfg["units"]:
                if not drivers.configured(uc) or uc.get("observe"):
                    continue
                s = drivers.read(ha, uc, cfg["names"], self._script_mem)
                cmds = drivers.release_commands(uc, s, cfg["names"], ha)
                for dom, svc, data, what in cmds:
                    try:
                        await ha.call_service(dom, svc, data)
                        self.event("act", f"Freigabe ({why}): {what}")
                    except Exception as e:  # noqa: BLE001
                        self.event("error", f"Freigabe fehlgeschlagen ({what}): {e}")
                    await asyncio.sleep(0.4)
                if uc.get("mode") and uc.get("fallback_mode"):
                    checks.append(uc)
                self._script_mem.pop(uc.get("name"), None)
            if checks:
                await asyncio.sleep(2.0)
                for uc in checks:
                    now = ha.state(uc["mode"])
                    if now == uc["fallback_mode"]:
                        self.event("info", f"✅ {uc['name']} ist wieder im Modus „{now}“")
                    else:
                        self.event("error", f"⚠️ {uc['name']}: Modus ist „{now}“ statt „{uc['fallback_mode']}“. Bitte in der Anker-App prüfen")
                        await self.notifier.send("⚠️ Freigabe unsicher", f"{uc['name']} meldet Modus „{now}“ statt „{uc['fallback_mode']}“. "
                                                 "Bitte in der Hersteller-App prüfen.", "release")
        finally:
            self._releasing = False

    async def shutdown(self):
        """Beim Beenden von SOLASI: Speicher freigeben, damit sie nicht mit altem Sollwert hängen bleiben."""
        cfg = self.cfg
        released = True
        if cfg["safety"]["release_on_stop"] and cfg["enabled"] and not cfg["dry_run"] and not self.stopped and self.ha.connected:
            self._shutdown = True                     # die laufende Regelung darf die Freigabe nicht überschreiben
            self.event("info", "SOLASI wird beendet: Speicher werden freigegeben")
            try:
                await asyncio.wait_for(self.release_all("Beenden"), timeout=8)
            except asyncio.TimeoutError:
                released = False
                self.event("error", "Freigabe beim Beenden hat zu lange gedauert")
        elif cfg["enabled"] and not cfg["dry_run"] and not self.stopped:
            released = False                          # keine Freigabe gewünscht: der Wächter soll eingreifen
        # Geordnetes Beenden melden, damit der Wächter nicht unnötig auslöst (nur wenn die Speicher frei sind)
        if released and self.ha.connected and self.ha.api_url:
            self._hb_stopped = True
            try:
                await self.ha.post_state("sensor.solasi_heartbeat", "stopped",
                                         {"friendly_name": "SOLASI Lebenszeichen", "icon": "mdi:heart-pulse"})
            except Exception as e:  # noqa: BLE001
                log.debug("Beenden nicht gemeldet: %s", e)

    async def _safety_check(self, snap, d):
        """Automatische Auslöser: Not-Aus-Schalter, Zählerausfall, Befehlsfehler und automatisches Fortsetzen."""
        cfg = self.cfg
        sf = cfg["safety"]
        now = time.monotonic()
        kill_ent = sf["kill_entity"]
        kill_on = bool(kill_ent) and self.ha.state(kill_ent) == "on"
        if kill_on and not self.stopped:
            await self.kill(f"Not-Aus-Schalter {kill_ent} ist an", "entity")
            return
        if self.stopped and self.safety["source"] == "entity" and not kill_on and kill_ent:
            self.resume()
            return
        if self.stopped:
            # automatisch gestoppt: optional selbstständig fortsetzen, wenn alles wieder in Ordnung ist
            healthy = d["meter_ok"] and len(self._fail_times) < 3
            self._clear_since = (self._clear_since or now) if healthy else None
            if (self.safety["source"] == "auto" and sf["resume_auto"] and self._clear_since
                    and now - self._clear_since >= self.resume_clear_s):
                self.resume()
            return
        if not d["meter_ok"]:
            self._meter_bad_since = self._meter_bad_since or now
            if sf["auto_meter_min"] and now - self._meter_bad_since >= sf["auto_meter_min"] * 60:
                await self.kill(f"Zähler seit {sf['auto_meter_min']:g} Minuten ohne Meldung", "auto")
                return
        else:
            self._meter_bad_since = None
        self._fail_times = [t for t in self._fail_times if now - t < 600]
        if sf["auto_errors"] and len(self._fail_times) >= 3:
            await self.kill("Steuerbefehle schlagen wiederholt fehl", "auto")

    async def _heartbeat_loop(self):
        """Lebenszeichen für den Wächter in Home Assistant (siehe watchdog.py)."""
        from datetime import datetime, timezone
        while True:
            try:
                if self.ha.connected and self.ha.api_url and not self._hb_stopped:
                    await self.ha.post_state("sensor.solasi_heartbeat", datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                             {"friendly_name": "SOLASI Lebenszeichen", "icon": "mdi:heart-pulse", "device_class": "timestamp"})
            except Exception as e:  # noqa: BLE001
                log.debug("Lebenszeichen nicht gesendet: %s", e)
            await asyncio.sleep(self.heartbeat_interval)

    heartbeat_interval = 30
    mode_retry_s = 30         # so selten wird versucht, einen von außen verstellten Modus zurückzusetzen
    resume_clear_s = 300      # so lange muss alles in Ordnung sein, bevor automatisch fortgesetzt wird

    # ---------- Lernen, Statistik, Selbsttest ----------
    def base_load_effective(self):
        so = self.cfg["soc"]
        v = self.learner.value
        if so.get("learn_base_load") and v is not None:
            return min(max(v * (1 + so["base_load_margin"] / 100.0), so["base_load_min"]), so["base_load_max"])
        return so["base_load"]

    def _after_cycle(self, snap, d):
        now_m = time.monotonic()
        house = snap["house_gross"]
        pv = (snap["pv_w"] + snap["extra_pv"]) if (snap["has_pv"] or snap["extra_pv"]) else None
        bat = snap.get("bat_w")
        self.stats.update(now_m, pv, house, snap["grid_w"], bat)
        night = is_night(pv if snap["has_pv"] else None, snap["sun"], datetime.now(timezone.utc).hour)
        self.learner.observe(time.time(), house, night)
        self._curtail_update(snap, d, now_m)
        self._trend_add(pv, house, bat)

    trend_every = 300
    trend_keep = 288

    def meter_view(self):
        """Zusätzliche Zähler und Tageswerte für Oberfläche und Karte (höchstens alle 5 Sekunden neu berechnet)."""
        now = time.monotonic()
        if self._meters_view is not None and now - self._meters_at < 5:
            return self._meters_view
        mc = self.cfg.get("meters") or {}

        def lookup(eid):
            st = self.ha.states.get(eid)
            if not st:
                return None
            at = st.get("attributes") or {}
            val = st.get("state")
            if val in (None, "unknown", "unavailable"):
                val = None
            return val, at.get("unit_of_measurement") or "", at.get("friendly_name") or ""

        day = self.stats.days.get(now_local().strftime("%Y-%m-%d"))
        k = Stats.kpis(day) if day else None
        self._meters_view = {
            "items": self.meters.compute(mc.get("items"), lookup, now_local().strftime("%Y-%m-%d")),
            "today": None if k is None else {"house": k["house"], "pv": k["pv"], "imp": k["imp"], "autarky": k["autarky"],
                                             "bat": k["bat_dis"], "chg": k["bat_chg"]},
            "show_day": bool(mc.get("show_day", True)), "extra": bool(mc.get("extra", False)),
            "order": clean_order(mc.get("order")),
        }
        self._meters_at = now
        return self._meters_view

    def trend_series(self):
        """Verlauf für Oberfläche und Karte: Zeit (Sekunden), Solar, Haus."""
        return {"t": [p[0] for p in self.trend], "pv": [p[1] for p in self.trend], "house": [p[2] for p in self.trend],
                "bat": [p[3] if len(p) > 3 else None for p in self.trend]}

    def _trend_add(self, pv, house, bat=None):
        """Kurzer Tagesverlauf für die Dashboard-Karte (Mittel je 5 Minuten, letzte 24 Stunden)."""
        acc = getattr(self, "_trend_acc", None)
        if acc is None:
            acc = self._trend_acc = {"t0": time.time(), "pv": [], "h": [], "b": []}
        if pv is not None:
            acc["pv"].append(pv)
        if house is not None:
            acc["h"].append(house)
        if bat is not None:
            acc["b"].append(max(0.0, bat))        # nur die Abgabe der Speicher
        if time.time() - acc["t0"] < self.trend_every:
            return
        avg = lambda v: round(sum(v) / len(v)) if v else None  # noqa: E731
        self.trend.append([int(time.time()), avg(acc["pv"]), avg(acc["h"]), avg(acc["b"])])
        self.trend = self.trend[-self.trend_keep:]
        self._trend_acc = None
        save_json(self._trend_path, {"p": self.trend})

    def _curtail_update(self, snap, d, now, hold_s=180):
        """Beobachtet, ob die Abregelung bei vollem Speicher wirkt (Einspeisung trotz vollem Speicher)."""
        cfg = self.cfg
        units = [u for u in snap["units"] if u["soc"] >= 0]
        full = bool(units) and all(u["soc"] >= u.get("max", cfg["soc"]["max"]) for u in units)
        sun_ok = (snap["pv_w"] + snap["extra_pv"] > 100) if (snap["has_pv"] or snap["extra_pv"]) else True
        active = bool(cfg["features"]["strict_zero"]) and full and sun_ok and d["meter_ok"]
        export = -snap["grid_w"]
        c = self.curtail
        c["export_w"] = round(export) if active else None
        bad = active and export > 40
        good = active and export <= 15
        self._curtail_bad = (self._curtail_bad or now) if bad else None
        self._curtail_good = (self._curtail_good or now) if good else None
        if self._curtail_bad and now - self._curtail_bad >= hold_s and c["state"] != "fehlgeschlagen":
            c.update(state="fehlgeschlagen", since=time.strftime("%d.%m. %H:%M"),
                     note=f"Speicher voll, trotzdem {round(export)} W Einspeisung. Verbraucher dürfen früher laufen.")
            self.event("error", "Abregelung greift nicht: Einspeisung trotz vollem Speicher")
        elif self._curtail_good:
            need = 600 if c["state"] == "fehlgeschlagen" else hold_s
            if now - self._curtail_good >= need and c["state"] != "ok":
                c.update(state="ok", since=time.strftime("%d.%m. %H:%M"),
                         note="Bei vollem Speicher wird nicht eingespeist: Die Abregelung wirkt.")
                self.event("info", "Abregelung bei vollem Speicher funktioniert")

    def _problems(self, snap, d):
        now = time.monotonic()
        self._fail_times = [t for t in self._fail_times if now - t < 600]
        units = snap["units"]
        valid = [u for u in units if u["soc"] >= 0]
        return {
            "meter": not d["meter_ok"],
            "offline": any(u["soc"] < 0 for u in units),
            "empty": bool(valid) and all(u["soc"] <= u.get("min", self.cfg["soc"]["min"]) for u in valid),
            "curtail": self.curtail["state"] == "fehlgeschlagen",
            "errors": len(self._fail_times) >= 3,
        }

    # ---------- Entitäten für Home Assistant (Dashboard-Karte, Verläufe, Automationen) ----------
    async def post_connect(self):
        """Wird nach (Wieder-)Verbindung aufgerufen."""
        self._published.clear()   # nach einem HA-Neustart sind die virtuellen Entitäten weg
        if self.card.get("installed") and self.card.get("base_url"):
            try:
                res = await self.ha.ensure_resource(self.card["base_url"], self.card["url"])
                self.card["resource"] = {"exists": "bereits registriert", "updated": "aktualisiert",
                                         "created": "registriert"}.get(res, res)
                if res != "exists":
                    self.event("info", f"Dashboard-Karte als Ressource {self.card['resource']}")
            except Exception as e:  # noqa: BLE001
                self.card["resource"] = "manuell"
                log.info("Ressource konnte nicht automatisch angelegt werden: %s", e)
        await self.sync_watchdog()
        await self.publish_entities()

    async def sync_watchdog(self):
        try:
            return await watchdog.sync(self)
        except Exception:  # noqa: BLE001
            log.exception("Wächter-Abgleich fehlgeschlagen")
            return self.watchdog

    def _set_wd_hash(self, h):
        self._wd_hash = h
        save_json(self._wd_path, {"hash": h})

    def _entity_payloads(self):
        st = self.status
        if not st:
            return {}
        if st.get("safety", {}).get("state") == "stopped":
            state = "Gestoppt"
        elif not st.get("enabled"):
            state = "Beobachten"
        elif st.get("meter_ok") is False:
            state = "Zähler-Ausfall"
        else:
            state = st.get("want", "Leerlauf")
        stopped = st.get("safety", {}).get("state") == "stopped"
        mode = "stopped" if stopped else ("observe" if not st.get("enabled") else ("test" if st.get("dry_run") else "live"))
        main = {
            "friendly_name": "SOLASI", "icon": "mdi:solar-power", "mode": mode,
            "enabled": st.get("enabled"), "dry_run": st.get("dry_run"),
            "flows": st.get("flows"),
            "pv_w": st.get("pv_w"), "house_w": st.get("house_w"), "grid_w": st.get("grid_w"),
            "battery_w": st.get("bat_w"), "target_w": st.get("t_target"),
            "surplus_w": st.get("surplus_w"), "avg_soc": st.get("avg_soc"),
            "kwh": st.get("kwh"), "cap_kwh": st.get("cap_kwh"), "limited": st.get("limited"),
            "eco_active": st.get("eco_active"), "meter_ok": st.get("meter_ok"),
            "blocked_w": st.get("blocked_w"), "want": st.get("want"),
            "units": st.get("units", []), "slots": st.get("slots", []),
            "stop_reason": st.get("safety", {}).get("reason", "") if stopped else "",
            "addon_slug": self.addon_slug,
            "card_version": self.card_version,
            "trend": self.trend_series(),
            "kill_switch": "switch.solasi_not_aus" if self.mqtt.active else "",
            "meters": self.meter_view()["items"], "today": self.meter_view()["today"],
            "meters_cfg": {"show_day": self.meter_view()["show_day"], "extra": self.meter_view()["extra"], "order": self.meter_view()["order"]},
        }
        out = {"sensor.solasi": (state, main)}
        if self.mqtt.active:
            return out                 # die Einzelwerte kommen dann als echte MQTT-Entitäten
        for key, eid, name, icon, val in (
            ("pv", "sensor.solasi_pv_power", "SOLASI Solarleistung", "mdi:solar-power", st.get("pv_w")),
            ("house", "sensor.solasi_house_power", "SOLASI Hausverbrauch", "mdi:home-lightning-bolt", st.get("house_w")),
            ("battery", "sensor.solasi_battery_power", "SOLASI Speicherleistung", "mdi:battery-charging", st.get("bat_w")),
            ("target", "sensor.solasi_target_power", "SOLASI Sollwert", "mdi:target", st.get("t_target")),
            ("surplus", "sensor.solasi_surplus_power", "SOLASI Überschuss", "mdi:flash", st.get("surplus_w")),
            ("base", "sensor.solasi_base_load", "SOLASI Grundlast (gelernt)", "mdi:home-clock", st.get("learned_base_load")),
        ):
            if val is None:
                continue
            out[eid] = (val, {"friendly_name": name, "icon": icon, "unit_of_measurement": "W",
                              "device_class": "power", "state_class": "measurement"})
        return out

    async def publish_entities(self):
        await self.mqtt.publish_state()
        if not self.ha.api_url:
            return
        for eid, (state, attrs) in self._entity_payloads().items():
            sig = json.dumps([state, attrs], sort_keys=True, default=str)
            if self._published.get(eid) == sig:
                continue
            try:
                await self.ha.post_state(eid, state, attrs)
                self._published[eid] = sig
                self._publish_failed = False
            except Exception as e:  # noqa: BLE001
                if not self._publish_failed:
                    self.event("error", f"Entitäten konnten nicht veröffentlicht werden: {e}")
                self._publish_failed = True
                return

    # ---------- Status für die Oberfläche ----------
    def _publish(self, snap, d):
        cfg = self.cfg
        house = snap["house_w"]
        if house is None and snap["has_out"]:
            house = max(snap["grid_w"] + snap["out_w"] + snap["extra_pv"], 0)
        pv_total = (snap["pv_w"] + snap["extra_pv"]) if (snap["has_pv"] or snap["extra_pv"]) else None
        self.status = {
            "flows": energy.flows(pv_total, snap.get("bat_w"), d["grid_w"]),
            "pv_w": round(snap["pv_w"] + snap["extra_pv"]) if (snap["has_pv"] or snap["extra_pv"]) else None,
            "bat_w": None if snap.get("bat_w") is None else round(snap["bat_w"]),   # Batterie: + Entladen, - Laden
            "house_w": None if house is None else round(house),
            "ts": time.strftime("%H:%M:%S"),
            "connected": self.ha.connected,
            "enabled": cfg["enabled"], "dry_run": cfg["dry_run"],
            "surplus_enabled": cfg["surplus"]["enabled"], "surplus_dry_run": cfg["surplus"]["dry_run"],
            "meter_ok": d["meter_ok"], "grid_w": round(d["grid_w"]),
            "net_balance": round(d["net_balance"]), "net_dis": round(d["net_dis"]),
            "t_target": round(d["t_target"]), "eco_active": d["eco_active"],
            "avg_soc": round(d["avg_soc"], 1), "blocked_w": round(d["blocked_w"]),
            "curtail": dict(self.curtail), "learned_base_load": self.learner.value, "safety": dict(self.safety),
            "base_load_used": round(self.base_load_effective()),
            "trend": self.trend_series(), "meter_view": self.meter_view(),
            "want": "Entladen" if d["want_dis"] else "Laden" if d["want_chg"] else "Leerlauf",
            "surplus_w": None if d["surplus_w"] is None else round(d["surplus_w"]),
            "units": [{
                "name": u["k"], "soc": u["soc"], "set": round(u["set"]), "real": round(u["real"]),
                "plan": u["p"], "force": u["force"], "available": u["has"], "pv": None if u.get("pv") is None else round(u["pv"]),
                "mode": u["mode"], "dir": u["dir"], "obs": u["obs"],
                "cap": u["cap"], "kwh": None if u["soc"] < 0 else round(max(0.0, min(100.0, u["soc"])) / 100 * u["cap"], 2),
                "ac": None if u.get("ac") is None else round(u["ac"]), "bat": None if u.get("bat") is None else round(u["bat"]),
                "locked": bool(u.get("locked")), "full": bool(u.get("full")),
                "min": u.get("min"), "max": u.get("max"), "lim_dis": u.get("lim_dis"), "lim_chg": u.get("lim_chg"),
            } for u in snap["units"]],
            "limited": any(u.get("locked") for u in snap["units"]),
            "kwh": round(d["kwh"], 2), "cap_kwh": round(d["cap_kwh"], 2),
            "slots": [{
                "name": s["name"], "ent": s["ent"], "num": s["num"],
                "state": snap["slots"][i]["ent_state"], "own_w": round(d["slot_own"][i]),
                "num_v": snap["slots"][i]["num_v"],
            } for i, s in enumerate(cfg["surplus"]["slots"]) if s["ent"] or s["num"]],
        }
