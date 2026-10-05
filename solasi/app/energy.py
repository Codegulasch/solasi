"""Energiefluss: verteilt die gemessenen Leistungen auf die Linien der Grafik.

Eingänge (alle in W, None = unbekannt):
  pv    Solarleistung der Module
  bat   Batterie netto: positiv = Entladen, negativ = Laden
  grid  Netz: positiv = Bezug, negativ = Einspeisung

Ausgänge (ganze Watt, None = nicht ableitbar):
  solar_house    Solar -> Haus
  solar_battery  Solar -> Speicher (die Ladeleistung der Batterie kommt zuerst aus der PV)
  battery_house  Speicher <-> Haus, positiv = Speicher -> Haus, negativ = Haus -> Speicher (Netzladen läuft über das Haus)
  grid_house     Netz <-> Haus, positiv = Netz -> Haus, negativ = Haus -> Netz

Der Hausverbrauch ergibt sich daraus (Zuflüsse minus Abflüsse am Haus):
  solar_house + max(battery_house, 0) + max(grid_house, 0) - max(-grid_house, 0) - max(-battery_house, 0)
"""


def _r(x):
    return None if x is None else int(round(x))


def flows(pv, bat, grid):
    out = {"solar_house": None, "solar_battery": None, "battery_house": None, "grid_house": _r(grid)}
    if bat is None:
        return out
    charge = max(-bat, 0.0)
    discharge = max(bat, 0.0)
    if pv is None:
        out["battery_house"] = _r(bat)                  # Woher die Ladung kommt, ist ohne PV-Wert nicht bekannt
        return out
    pv = max(pv, 0.0)
    to_battery = min(charge, pv)                        # Solar lädt die Batterie so weit, wie sie lädt
    from_grid = max(charge - to_battery, 0.0)           # der Rest der Ladung kommt aus dem Netz (über das Haus)
    out["solar_battery"] = _r(to_battery)
    out["solar_house"] = _r(max(pv - to_battery, 0.0))
    out["battery_house"] = _r(discharge - from_grid)
    return out
