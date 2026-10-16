"""Systemprüfung: prüft Entitäten, Optionen und Voraussetzungen und gibt Hinweise."""
import drivers
from ha import is_num


def run(cfg, ha, ctrl=None):
    items = []

    def add(area, item, status, text, hint=""):
        items.append({"area": area, "item": item, "status": status, "text": text, "hint": hint})

    def exists(eid):
        return eid in ha.states

    def check_entity(area, label, eid, domain=None, numeric=False, required=True, unit_w=False):
        if not eid:
            if required:
                add(area, label, "error", "nicht ausgewählt", "Unter „Einstellungen → Anlage“ auswählen.")
            else:
                add(area, label, "info", "nicht gewählt (optional)")
            return False
        if not exists(eid):
            add(area, label, "error", f"{eid} existiert nicht", "Entität prüfen. Hat sie sich umbenannt?")
            return False
        if domain and not eid.startswith(domain + "."):
            add(area, label, "warn", f"{eid} ist keine {domain}-Entität", f"Hier wird eine Entität vom Typ „{domain}“ erwartet.")
        state = ha.state(eid)
        if numeric:
            if state in ("unavailable", "unknown"):
                add(area, label, "warn", f"{eid}: {state}", "Gerät oder Integration offline?")
                return True
            if not is_num(state):
                add(area, label, "error", f"{eid}: „{state}“ ist keine Zahl")
                return True
            if unit_w:
                unit = ha.attr(eid, "unit_of_measurement")
                if unit and unit.lower() == "kw":
                    add(area, label, "warn", f"{eid} liefert kW statt W", "SOLASI erwartet Watt. Einheit per Template-Sensor umrechnen.")
                    return True
        add(area, label, "ok", f"{eid} = {state}")
        return True

    # ---- Verbindung ----
    add("Verbindung", "Home Assistant", "ok" if ha.connected else "error",
        "verbunden" if ha.connected else "keine Verbindung")

    # ---- Zähler ----
    g = cfg["grid"]
    if check_entity("Zähler", "Netzleistung", g["entity"], "sensor", numeric=True, unit_w=True):
        age = ha.age_seen(g["entity"])
        if age == float("inf"):
            add("Zähler", "Aktualität", "info", "seit dem Start noch keine Meldung empfangen")
        elif cfg["features"]["failsafe"] and g["max_age"] and age > g["max_age"]:
            add("Zähler", "Aktualität", "warn", f"letzte Meldung vor {int(age)} s",
                "Der Zähler meldet seltener als der eingestellte Ausfall-Zeitraum. Zeitraum erhöhen oder Sensor prüfen.")
        else:
            add("Zähler", "Aktualität", "ok", f"letzte Meldung vor {int(age)} s")

    # ---- Speicher ----
    names = cfg["names"]
    configured = 0
    labels = {"anker": "Betrag + Richtung", "signed": "Zahl mit Vorzeichen", "modal": "Modus + Leistungen",
              "limit": "Ausgangslimit", "script": "Skript"}

    def check_options(area, label, eid, wanted, hint_name):
        opts = ha.attr(eid, "options") or []
        missing = [o for o in wanted if o and opts and o not in opts]
        if missing:
            add(area, label, "error", f"Option(en) fehlen: {', '.join(missing)} (vorhanden: {', '.join(opts)})", hint_name)
        elif opts:
            add(area, label, "ok", ", ".join(opts))

    for u in cfg["units"]:
        obs = bool(u.get("observe"))
        if obs:      # beobachtet: keine Steuer-Felder prüfen
            u = dict(u, num="", dir="", mode="", enable="", num_chg="", fallback_mode="", script="")
        area = u["name"] if u["name"].lower().startswith("speicher") else f"Speicher {u['name']}"
        d = drivers.driver(u)
        if not (drivers.entities(u) or u["soc"] or u["pv"]):
            continue
        configured += 1
        o = drivers.opts(u, names)
        add(area, "Speichertyp", "info", labels[d])
        if obs:
            add(area, "Steuerung", "info", "Nur beobachten: SOLASI liest die Werte und schreibt nichts auf diesen Speicher")
        if not drivers.configured(u) and not obs:
            add(area, "Konfiguration", "error", "Für diesen Speichertyp fehlen Pflichtfelder",
                {"anker": "Leistung (number) und Richtung (select) wählen.", "signed": "Leistung (number) wählen.",
                 "limit": "Limit (number) wählen.", "modal": "Modus (select) und Entladeleistung (number) wählen.",
                 "script": "Skript wählen."}[d])
        if d in ("anker", "signed", "limit", "modal") and u["num"]:
            label = {"modal": "Entladeleistung (number)", "limit": "Ausgangslimit (number)"}.get(d, "Leistung (number)")
            ok_num = check_entity(area, label, u["num"], "number", numeric=True)
            if ok_num and ha.state(u["num"]) in ("unavailable", "unknown"):
                items[-1]["hint"] = ("Normal, solange der Speicher nicht im Modus „%s“ ist. SOLASI schaltet ihn beim Start der Regelung um."
                                     % (o["mode"] or "für externe Steuerung") if (u["mode"] and o["mode"])
                                     else "Gerät oder Integration offline?")
            if ok_num:
                nmax = ha.attr(u["num"], "max")
                if isinstance(nmax, (int, float)) and u["max_dis"] > nmax:
                    add(area, "Max. Entladeleistung", "warn", f"{u['max_dis']} W liegt über dem Maximum der Entität ({nmax} W)",
                        "Wert in den Einstellungen anpassen.")
        if d == "modal" and u["num_chg"]:
            check_entity(area, "Ladeleistung (number)", u["num_chg"], "number", numeric=True)
        if d == "modal" and not u["num_chg"]:
            add(area, "Ladeleistung (number)", "info", "nicht gewählt: dieser Speicher wird nicht aus dem Netz geladen")
        if d in ("anker", "modal") and not obs:
            lbl = "Richtung (select)" if d == "anker" else "Modus Stop/Laden/Entladen (select)"
            if check_entity(area, lbl, u["dir"], "select"):
                check_options(area, "Richtungs-Optionen" if d == "anker" else "Modus-Optionen", u["dir"],
                              [o["dis"], o["chg"]] + ([o["stop"]] if d == "modal" else []),
                              "Namen im Speicher (Experten-Modus) oder global unter „Sicherheit & Meldungen → Namen der Optionen“ anpassen.")
        if d == "script" and not obs:
            check_entity(area, "Skript", u["script"], "script")
            add(area, "Aufruf", "info", "Das Skript erhält die Felder power_w (+ Entladen, − Laden), mode und unit.")
        if u["enable"]:
            check_entity(area, "Fernsteuerung (Schalter)", u["enable"])
        if u["mode"]:
            if check_entity(area, "Arbeitsmodus (select)", u["mode"], "select"):
                if o["mode"]:
                    check_options(area, "Modus-Option", u["mode"], [o["mode"]],
                                  "Option im Speicher oder global unter „Sicherheit & Meldungen → Namen der Optionen“ anpassen.")
        elif d == "anker" and not obs:
            add(area, "Betriebsmodus (select)", "warn", "nicht gewählt",
                "Ohne Modus-Wächter muss der Speicher von Hand im externen Modus bleiben.")
        # Rückfall für den Kill-Switch
        fb = u.get("fallback_mode")
        if u["mode"] and fb:
            opts_ = ha.attr(u["mode"], "options") or []
            if opts_ and fb not in opts_:
                add(area, "Rückfall-Modus", "error", f"„{fb}“ nicht vorhanden (vorhanden: {', '.join(opts_)})",
                    "Beim Stoppen kann der Speicher so nicht zurückgegeben werden. Option korrigieren.")
            else:
                add(area, "Rückfall-Modus", "ok", f"„{fb}“ (wird beim Stoppen gesetzt)")
        elif d in ("anker", "signed", "modal") and u["mode"]:
            add(area, "Rückfall-Modus", "warn", "nicht gewählt",
                "Beim Stoppen bleibt der Speicher im externen Modus (mit 0 W). Wähle den Modus, den er danach haben soll, z. B. Eigenverbrauch.")
        elif d == "anker" and not obs:
            add(area, "Rückfall-Modus", "warn", "kein Betriebsmodus gewählt",
                "Ohne Betriebsmodus kann SOLASI den Speicher beim Stoppen nicht auf Eigenverbrauch zurückstellen.")
        if check_entity(area, "Ladestand (SOC)", u["soc"], "sensor", numeric=True):
            v = ha.state(u["soc"])
            if is_num(v) and not (0 <= float(v) <= 100):
                add(area, "SOC-Wert", "warn", f"{v} liegt nicht zwischen 0 und 100")
        if u["power"]:
            check_entity(area, "Echte Leistung (Sensor mit Vorzeichen)", u["power"], "sensor", numeric=True, unit_w=True)
        else:
            for key, label in (("real_dis", "Echte Entladeleistung"), ("real_chg", "Echte Ladeleistung")):
                if u[key]:
                    check_entity(area, label, u[key], "sensor", numeric=True, unit_w=True)
                else:
                    add(area, label, "warn", "nicht gewählt (empfohlen)",
                        "Wird für Failsafe, Hausverbrauch, Statistik und Grundlast-Lernen gebraucht.")
        if u["pv"]:
            check_entity(area, "PV-Leistung", u["pv"], "sensor", numeric=True, unit_w=True)
        else:
            add(area, "PV-Leistung", "info", "nicht gewählt (optional)",
                "Für PV-Durchleitung bei leerem Speicher, Überschuss aus PV, Statistik und Replay nötig.")
        # Messart der Leistungssensoren (AC oder Batterie) und Plausibilität
        fl = drivers.flows(ha, u)
        if fl["has"]:
            b = fl["basis"]
            add(area, "Messart der Leistungssensoren", "info",
                ("Leistung am Hausanschluss (AC)" if b == "ac" else "Leistung an der Batterie (DC)")
                + ("" if u.get("power_basis") else " (automatisch)"))
            if b == "battery" and not u["pv"]:
                add(area, "Messart Batterie", "error", "braucht den PV-Sensor dieses Speichers",
                    "Ohne PV-Leistung lässt sich die Abgabe ins Haus nicht berechnen.")
            grid_v = drivers.sensor_num(ha, cfg["grid"]["entity"]) if cfg["grid"]["entity"] else None
            chg_v = drivers.sensor_num(ha, u.get("real_chg")) if u.get("real_chg") else None
            if (b == "ac" and chg_v is not None and chg_v > 30 and grid_v is not None and abs(grid_v) < 40
                    and fl["pv"] is not None and fl["pv"] >= chg_v - 20):
                add(area, "Plausibilität", "warn",
                    f"Ladeleistung {chg_v:.0f} W bei Netz {grid_v:.0f} W und PV {fl['pv']:.0f} W",
                    "Das sieht nach der Lade-Leistung der Batterie aus, nicht nach Netzbezug. Stelle die Messart auf „Batterie“.")
        if u["pv"] and fl["pv"] is None and ha.state(u["pv"]) is not None:
            add(area, "PV-Leistung", "warn", "liefert gerade keinen Wert",
                "SOLASI behandelt das als unbekannt (nicht als 0 W). Prüfe, ob der richtige Sensor gewählt ist.")
    if configured == 0:
        add("Speicher", "Konfiguration", "error", "Kein Speicher eingerichtet")

    # ---- Energiebilanz ----
    if configured:
        fls = [(u, drivers.flows(ha, u)) for u in cfg["units"] if (drivers.configured(u) or u.get("observe"))]
        gv = drivers.sensor_num(ha, cfg["grid"]["entity"]) if cfg["grid"]["entity"] else None
        pv_known = [f_["pv"] for _, f_ in fls if f_["pv"] is not None]
        ac_known = [f_["ac"] for _, f_ in fls if f_["has"]]
        if gv is not None and fls and all(f_["has"] and f_["ac"] is not None for _, f_ in fls):
            ac_sum = sum(f_["ac"] for _, f_ in fls)
            house = max(gv + ac_sum, 0)
            bat = sum(f_["bat"] for _, f_ in fls if f_["bat"] is not None)
            add("Energiebilanz", "Berechnet", "info",
                f"Solar {sum(pv_known):.0f} W · Batterie {bat:+.0f} W · Abgabe ins Haus {ac_sum:.0f} W · Netz {gv:.0f} W → Haus {house:.0f} W",
                "Vergleiche das mit der Hersteller-App. Weichen Solar, Batterie oder Haus ab, stimmt die Sensorauswahl oder die Messart nicht.")
            hs = cfg["surplus"]["house"]
            hv = drivers.sensor_num(ha, hs) if hs else None
            if hv is not None and abs(hv - house) > 100:
                add("Energiebilanz", "Hausverbrauch-Sensor", "warn", f"Sensor {hv:.0f} W, berechnet {house:.0f} W",
                    "Die Werte weichen deutlich ab. Prüfe Messart und Sensoren.")
        else:
            add("Energiebilanz", "Berechnet", "warn", "nicht berechenbar",
                "Es fehlen Zählerwert, Leistungssensoren oder (bei Messart Batterie) die PV-Leistung.")

    # ---- Überschuss ----
    sp = cfg["surplus"]
    if sp["enabled"]:
        for i, s in enumerate(sp["slots"]):
            if not (s["ent"] or s["num"]):
                continue
            area = f"Verbraucher {s['name']}"
            if s["ent"]:
                check_entity(area, "Schalter", s["ent"])
            if s["num"]:
                if check_entity(area, "Vorgabe (number)", s["num"], "number"):
                    if ha.attr(s["num"], "step") is None:
                        add(area, "Schrittweite", "info", "keine Schrittweite hinterlegt, es wird 1 verwendet")
        if sp["source"] == "pv" and not any(u["pv"] for u in cfg["units"]):
            add("Überschuss", "Quelle", "warn", "„PV minus Hausverbrauch“ gewählt, aber kein PV-Sensor",
                "Es wird die Einspeisung als Überschuss verwendet.")

    # ---- Sicherheit ----
    sf = cfg["safety"]
    if sf["kill_entity"]:
        check_entity("Sicherheit", "Not-Aus-Schalter", sf["kill_entity"])
    add("Sicherheit", "Freigabe beim Stoppen", "ok" if sf["release_on_stop"] else "warn",
        "an" if sf["release_on_stop"] else "aus", "" if sf["release_on_stop"] else "Beim Stoppen oder Beenden bleiben die Speicher im externen Modus.")
    add("Sicherheit", "Automatisch stoppen bei Zählerausfall", "ok" if sf["auto_meter_min"] else "info",
        f"nach {sf['auto_meter_min']:g} Minuten" if sf["auto_meter_min"] else "aus")
    if ctrl is not None and ctrl.stopped:
        add("Sicherheit", "Aktueller Zustand", "warn", f"GESTOPPT: {ctrl.safety['reason']}", "Unter „Übersicht“ mit „Fortsetzen“ wieder starten.")

    # ---- Zusatzfunktionen ----
    n = cfg["notify"]
    add("Benachrichtigungen", "Ziel", "ok" if n["service"] else "info",
        n["service"] or "nicht eingerichtet", "" if n["service"] else "Unter „Einstellungen → Sicherheit & Meldungen“ auswählen.")
    if ctrl is not None and getattr(ctrl, "mqtt", None) is not None:
        ms = ctrl.mqtt.status
        if ms["state"] == "verbunden":
            add("Verbindung", "MQTT-Entitäten", "ok", f"verbunden ({ms['host']})")
        elif ms["state"] == "aus":
            add("Verbindung", "MQTT-Entitäten", "info", "ausgeschaltet", "Einfache Sensoren werden verwendet.")
        else:
            add("Verbindung", "MQTT-Entitäten", "warn", ms.get("detail") or "noch nicht verbunden",
                "Optional: Mosquitto-Add-on installieren, dann legt SOLASI feste Entitäten an. Siehe System → Entitäten (MQTT).")
    if ctrl is not None:
        house_known = ctrl.last_snap is not None and ctrl.last_snap.get("house_gross") is not None
        add("Lernen & Statistik", "Hausverbrauch", "ok" if house_known else "warn",
            "wird berechnet" if house_known else "nicht berechenbar",
            "" if house_known else "Dafür die echten Lade-/Entladesensoren der Speicher oder einen Hausverbrauchs-Sensor wählen.")
        add("Dashboard-Karte", "Installation", "ok" if ctrl.card.get("installed") else "warn",
            "installiert" if ctrl.card.get("installed") else "nicht automatisch installiert", "Siehe System → Dashboard-Karte.")
    if cfg["control"]["total_max_dis"] > 800:
        add("Hinweis", "Gesamtlimit Entladung", "info", f"{cfg['control']['total_max_dis']} W",
            "Über 800 W Einspeiseleistung: bitte prüfen, ob die Anlage entsprechend angemeldet ist.")

    summary = {k: sum(1 for i in items if i["status"] == k) for k in ("ok", "warn", "error", "info")}
    return {"items": items, "summary": summary}
