# SOLASI – Guide

🇩🇪 [Deutsche Version](DOCS.md)

> **🧪 Beta:** SOLASI is still in beta. It was developed on a system with Anker SOLIX (Solarbank 4) and has been tested in everyday use; other storage types are implemented according to the descriptions of their integrations and have so far only been checked in simulations. It controls real hardware, so errors are possible. Always start in **Testmodus** (test mode), keep the **Not-Aus** (emergency stop) in view, and try new functions (for example grid charging and discharge lock) with short tests first. Use is at your own risk. Feedback and bug reports are welcome.

SOLASI controls your battery storage so that your house uses as much of its own solar power as possible: hardly any feed-in to the grid, hardly any draw from the grid.
You make all settings in the SOLASI interface (sidebar in Home Assistant); you do not need a configuration file.

> **Important:** SOLASI controls real hardware. Always start in **Testmodus** (step 5 of the setup) and get to know the **Not-Aus** (chapter "Safety and Not-Aus (emergency stop)").

## Contents

1. [Prerequisites](#prerequisites)
2. [Setup step by step](#setup-step-by-step)
3. [The interface](#the-interface)
4. [Storage types](#storage-types)
5. [Control and settings](#control-and-settings)
6. [Surplus for appliances, wall box and heating element](#surplus-for-appliances-wall-box-and-heating-element)
7. [Safety and emergency stop](#safety-and-emergency-stop)
8. [Notifications](#notifications)
9. [Evaluation: Statistics and Replay](#evaluation-statistics-and-replay)
10. [Self-test and energy balance](#self-test-and-energy-balance)
11. [Dashboard card](#dashboard-card)
12. [Fixed entities and Energy dashboard (MQTT)](#permanent-entities-and-energy-dashboard-mqtt)
13. [Backing up your settings](#backing-up-the-settings)
14. [FAQ and troubleshooting](#faq-and-troubleshooting)
15. [Privacy and liability](#privacy-and-liability)

## Prerequisites

- Home Assistant with the add-on store (Home Assistant OS or Supervised).
- Your storage is integrated into Home Assistant. For the **Anker SOLIX Solarbank 4 E5000 Pro**, via the official integration *Anker Solix Official*.
- A **sensor for grid power in watts** (positive = draw, negative = feed-in), for example a reading head on the electricity meter or a Shelly EM.
  Ideally the raw or briefly smoothed value, not an average over minutes, otherwise the control reacts sluggishly.
- Recommended: sensors for the **solar power** and for **charging and discharging** of your storage.

If you currently use an automation or blueprint for zero feed-in, **turn it off** before SOLASI controls live. Two controllers working at the same time work against each other.

## Setup step by step

1. **Open SOLASI.** The welcome page leads you to *Einrichtung* (Setup).
2. **Choose the meter.** Enter the grid power sensor. If your meter shows feed-in as a positive value, turn on "Vorzeichen umkehren" (Reverse sign).
3. **Set up the storage.** Choose the **Speichertyp** (storage type) and the matching entities. The fields suggest them; the sensors of the same device are listed first with their current value.
   For the Anker SOLIX these are:
   - **Leistung (number)** (Power): the "Leistungssteuerung" (power control) entity
   - **Leistungsfluss / Richtung (select)** (Power flow / direction): charge or discharge
   - **Betriebsmodus (select)** (Operating mode): the mode of the storage. SOLASI switches it to external control (`third_party_control`)
   - **Ladestand (SOC)** (state of charge) and, recommended, **PV-Leistung** (PV power), **Entlade-** (discharge) and **Ladeleistung** (charge power)
   - **Beim Stoppen: Modus setzen auf** (When stopping: set mode to): the mode the storage receives when SOLASI stops, usually "self_consumption" for Anker (called "Eigenverbrauch" in the Anker app)
4. **Check the measurement type.** Do your charge and discharge sensors measure the battery or the output to the house? For Anker with a PV sensor, "Automatisch" (Automatic) is correct. Details in the chapter [Self-test and energy balance](#self-test-and-energy-balance).
5. **Start in test mode.** At the top, turn on **Regelung** (Control) and leave **Testmodus** (test mode) on. SOLASI then calculates everything but sends nothing. Under *System → Protokoll* (System → Log) you can see what would happen
   (for example "Test: Speicher A: 0 W → 280 W").
6. **Run the self-test** (*System → Selbsttest*, System → Self-test). It reports missing or wrong entities with a suggested solution.
7. **Go live.** When direction and values look plausible, **turn off Testmodus**. From now on SOLASI controls the storage and, if necessary, puts it into external control.

The switches at the top take effect immediately and are saved automatically. Changes in the forms only apply after **Speichern** (Save).

## The interface

The sidebar is on the left; on a phone there is a bar at the bottom (the rest is in the **Mehr** (More) menu).

| Area | Content |
|---|---|
| **Betrieb** (Operation) | *Übersicht* (Overview: key figures, meter, energy flow, storage, surplus, log), *Speicher* (Storage), *Überschuss* (Surplus), *Zähler* (Meter) |
| **Auswertung** (Evaluation) | *Statistik* (Statistics) and *Replay* |
| **System** | *Selbsttest* (Self-test), *Protokoll* (Log), *Dashboard-Karte* (Dashboard card), *Entitäten (MQTT)* (Entities (MQTT)) |
| **Einrichtung** (Setup) | Set up meter and storage, also as a wizard on first start |
| **Einstellungen** (Settings) | *Regelung* (Control), *Sicherheit & Meldungen* (Safety & Notifications), *Darstellung* (Appearance) |

The header shows connection and mode (**Live**, **Testmodus** (test mode), **Beobachten** (Observing) or **Gestoppt** (Stopped)) and contains the switches **Regelung** (Control) and **Testmodus** as well as the **Not-Aus** (emergency stop), which asks for confirmation before triggering.
A notice bar appears when something needs attention. Under *Einstellungen → Darstellung* (Settings → Appearance) you choose the start page and density; both apply only to the respective device.

**The history chart** below the energy flow shows the last 24 hours: solar as an area, house as a line, the dot is the current value. The dashboard card shows the same graphic.

**Reading the energy flow:** The battery's charging power comes first from the solar power (line *Solar → Speicher*, Solar → Storage), the rest goes to the house. If the solar power is not enough, the rest of the charge comes from the grid
and flows through the house into the storage. When discharging, the storage delivers via the line *Speicher → Haus* (Storage → House). The distribution is derived from the measured values; the system does not report it itself.
SOLASI shows unknown values as "–", never as 0 W.

## Storage types

SOLASI is not tied to one manufacturer. For each storage you choose the **Speichertyp** (storage type) under *Einrichtung* (Setup). Types can be mixed.

| Type | How it is controlled | Suits e.g. |
|---|---|---|
| Anker SOLIX (Betrag + Richtung) (amount + direction) | A number for the power, a selection for the direction | Anker Solarbank 4 E5000 Pro |
| Eine Zahl mit Vorzeichen (One signed number) | One number: positive = discharge, negative = charge (can be reversed), optional working mode | Marstek in passive mode |
| Modus + Leistungen (Mode + powers) | Selection Stop / Charge / Discharge plus numbers for discharge and charge power, optional remote control and working mode | Marstek via Modbus |
| Ausgangslimit (nur Entladen) (Output limit, discharge only) | One number limits the output, no charging from the grid | Inverter limit (e.g. via OpenDTU) |
| Eigenes Skript (Custom script) | Calls a Home Assistant script | everything else (Victron, Huawei, Sungrow …) |

Storage types without grid charging (output limit, mode without a charge number) are never scheduled to charge when there is surplus.

**Capacity and total state of charge:** For each storage, enter the usable capacity in kWh (*Einrichtung*, for example 5 or 10). The total state of charge in the energy flow is then weighted by capacity and is also shown in kWh. With the default value of 5 kWh for every storage it would otherwise be a simple average.

**Observe only:** If the manufacturer's app controls a storage itself (for example Anker Solix with smart meter and zero export), turn on "Nur beobachten" (Observe only) for that storage. SOLASI then reads the state of charge and the real power sensors, but writes nothing to the storage, sets no mode and does not hand it back when stopping. Power and direction do not need to be entered. SOLASI controls the rest with the other storages. Its contribution still appears in the energy flow, the history chart and the total state of charge.

**Discharge limit and upper charge limit:** Many storages have their own limits (adjustable in the app for Anker). Below the discharge limit the storage delivers nothing, above the upper charge limit it does not charge, no matter what SOLASI requests. For each storage, enter the entities "Entladegrenze" (discharge limit) and "Ladeobergrenze" (upper charge limit) (*Einrichtung*, both optional). SOLASI then uses the higher of the discharge limit and its own minimum state of charge as the minimum state of charge, and considers the storage full from the upper charge limit. With the switch **"Grenzen in den Speicher schreiben"** (Write limits to the storage) (per storage), SOLASI writes its own values there: the minimum state of charge into the discharge limit, the maximum state of charge into the upper charge limit. Each storage can have its **own minimum and maximum state of charge**; if left empty, the global value from "Akku-Grenzen & Eco" (Battery limits & Eco) applies. SOLASI checks every few minutes and resets deviating values, even if they were changed in the manufacturer's app. Without the switch, SOLASI only reads the values. Hysteresis and Eco stay in SOLASI. The self-test shows target and actual value per storage.

**Emergency power reserve:** If you enter the entity "Notstromreserve" (emergency power reserve) for a storage (optional, read only), SOLASI treats it like the discharge limit: below it the storage delivers nothing, and the minimum state of charge is the highest value of its own minimum, discharge limit and emergency power reserve.

**Transferring surplus to another storage:** If one storage is full and another can charge via AC ("Laden aus dem Netz" (Charging from the grid) on, power flow option for charging available), SOLASI does not throttle the full one. The solar power of the full storage is fed in, and the other one charges it back in as soon as the surplus is above the switch-on threshold. This causes conversion losses of about 10–15 %, and the measured house consumption also rises by the charging power. SOLASI shows this share as "durchgereicht" (passed through) (house tile without charging power) and excludes it from daily consumption, self-sufficiency and base load learning; this can be switched off under *Darstellung → Energiefluss* (Appearance → Energy flow). With the switch *Überschuss in anderen Speicher umladen* (Transfer surplus to another storage) (*Funktionen*, Functions) you can turn this off, and the system then throttles as before. If all storages are full, it always throttles.

**Configuring the energy flow:** Under *Einstellungen → Darstellung → Energiefluss* (Settings → Appearance → Energy flow) you choose the template (total solar on top, pairs, compact), show or hide tiles, set the position of the grid and sort the systems. The dashboard card adopts the setting. Per card this works with `flow_layout` (auto, total, pairs, compact), `flow_hide` (list of total, solar, bat, grid, house), `flow_grid_pos` (auto, mid, side) and `flow_order` (list of system names).

**Storage that delivers nothing:** If SOLASI requests more than 30 W from a storage and nothing arrives (under 10 W) for about 90 seconds, it is considered "locked", for example because of a limit in the device. The display shows "Grenze" (limit), the headline states it, and the other storage takes over. If the state of charge rises by 3 percentage points or 20 minutes have passed, SOLASI asks it again. This applies only with control switched on and without Testmodus, and not to storages in "Nur beobachten" mode. The headline always shows what is actually flowing, not the target value.

**Storage in the overview and statistics:** The tile "Aus Speichern heute" (From storage today) (with the charged amount below it) appears when *Zähler → Solarertrag, Netzbezug und Speicher heute dazu* (Meter → Add solar yield, grid draw and storage today) is switched on. The chart in *Statistik* (Statistics) additionally shows how much came from the storages each day. The values start on the first day SOLASI uses this version.

**Menu on the phone:** On small screens the quick bar with *Übersicht* (Overview), *Speicher* (Storage), *Statistik*, *Überschuss* (Surplus) and "Mehr" (More) is at the top so that it does not disappear behind the browser bar.

**Color gradient of the card:** Like the overview in the add-on, the dashboard card has a soft gradient in the background. With the card option `gradient: false` (in the editor "Farbverlauf im Hintergrund", Gradient in the background) it stays a single color; `accent` changes the color.

> **Status:** The Anker SOLIX was developed and tested in practical use. The other types are implemented according to the descriptions of the respective integrations and have so far only been checked in simulations.
> Please observe them in Testmodus first, and feel free to give feedback.

**Custom script:** SOLASI calls the script with these fields. When handing the storage back (Not-Aus), `mode` equals `release` and `power_w` equals 0.

```yaml
script:
  mein_speicher_setzen:
    fields:
      power_w: { description: "Sollwert in W: positiv = Entladen, negativ = Laden" }
      mode:    { description: "discharge, charge, idle oder release" }
      unit:    { description: "Name des Speichers" }
    sequence:
      - action: number.set_value
        target: { entity_id: number.mein_speicher_leistung }
        data: { value: "{{ power_w }}" }
```

For a script, SOLASI remembers the last setpoint sent, because it cannot be read back.

## Control and settings

### How SOLASI controls
SOLASI reads the meter and calculates the setpoint for the storage from it. It deliberately leaves a few watts of grid draw (default 10 W) so that no battery power flows into the grid.
With two storages, the setpoint is split: evenly, by state of charge, or one after the other.

### Functions (*Einstellungen → Regelung*, Settings → Control)
Each function can be switched on and off individually.

| Function | What it does |
|---|---|
| **Eco-Modus** (Eco mode) | Limits the output from the battery to the base load at a low state of charge so that the battery lasts until morning. Solar power additionally goes directly to the house |
| **Schwellen verwenden** (Use thresholds) | Reacts only from a minimum deviation (default 120 W on, 80 W off). Prevents erratic switching |
| **Laden aus Fremd-Überschuss erlauben** (Allow charging from third-party surplus) | The battery may also be charged with surplus from other generators at the meter |
| **Strenge Nulleinspeisung bei vollem Speicher** (Strict zero feed-in when storage is full) | A full storage is set to "Entladen" (discharge) so that the solar power is throttled instead of going into the grid. Whether the storage implements this depends on its firmware. The self-test observes it |
| **Externe Steuerung automatisch einschalten** (Switch on external control automatically) | As soon as SOLASI controls live, it sets the storage's operating mode to external control (`third_party_control` for Anker): at start, after "Fortsetzen" (Resume), and when the mode is changed from outside. The Not-Aus is used to hand it back |
| **PV direkt ins Haus geben, auch bei leerem Speicher** (Pass PV directly to the house, even when the storage is empty) | If the state of charge is below the minimum, the storage may still deliver as much as its modules are currently producing. The battery is not discharged in the process. Needs the PV sensor |
| **Failsafe** | If the meter fails, the storages go to 0 W. If power is still flowing although 0 W is intended, 0 W is sent again |

### Limits and battery
- **Gesamtlimit Entladung / Laden** (Total limit discharge / charge)**:** The default is a cautious 800 W for output. Adjust it to your system and the requirements of your grid operator.
- **Nicht entladen unter / Nicht laden über** (Do not discharge below / Do not charge above)**:** State-of-charge limits (default 15 % and 99 %). A hysteresis prevents switching back and forth at the limit.
- **Eco-Modus ab mittlerem Ladestand** (Eco mode from average state of charge) (default 35 %) and **Eco-Entladeleistung** (Eco discharge power) (150 W) determine when and how strongly Eco brakes.
- **Learning the base load:** With "Eco-Leistung aus gelernter Grundlast" (Eco power from learned base load), SOLASI measures your house's consumption at night and adjusts the Eco power itself (median of the last seven nights plus a margin).
  This requires sensors for charging and discharging or a house consumption sensor. The learned value is shown in the settings and as `sensor.solasi_base_load`.

### Sensors and measurement type
Under *Einrichtung* (Setup), each storage shows the **sensors of the same device with their current value**. Compare them with the manufacturer's app to find solar, charging and discharging.

**Measurement type of the power sensors:**

| Measurement type | Meaning | Output to the house |
|---|---|---|
| Batterie (DC) (Battery) | Charge and discharge power of the battery (typical for Anker) | Solar + battery |
| Haus-Anschluss (AC) (House connection) | Power that the storage delivers to the house or draws from the grid | measured directly |

"Automatisch" (Automatic) takes the battery side for Anker with a PV sensor, otherwise AC. Anker example: 540 W solar, battery charges 140 W → 400 W go to the house.

## Surplus for appliances, wall box and heating element

Under *Betrieb → Überschuss* (Operation → Surplus) you set up to **three appliances** that run when there is more solar power than the house needs. This is also where you switch the function on.
The **Überschuss-Test** (Surplus test) only logs what would be switched.

- **Source of the surplus:** *PV minus Hausverbrauch* (PV minus house consumption; recommended, needs PV sensors), *Einspeisung ins Netz* (Feed-in to the grid) or an *eigener Sensor* (own sensor).
- **Switching on and off:** Each appliance has a switch-on threshold (surplus in watts), a switch-off threshold (deficit), delays, minimum run time and minimum pause. The appliances have an order,
  the first has priority. Lower priorities sensibly get smaller switch-off thresholds so that they turn off first.
- **State-of-charge condition:** Appliances only run once the average state of charge has reached a value. This way the storages take priority.
- **Continuously variable (wall box, heating element):** Enter an entity (number) for the charging current or power, plus the **Watt pro Einheit** (watts per unit) (wall box single-phase 230 W per ampere, three-phase 690 W per ampere, heating element in watts: 1),
  minimum and maximum power. SOLASI tracks the value to the surplus and rounds down to the step size of the entity so that it never exceeds the surplus.
- **Nicht aus dem Akku versorgen** (Do not supply from the battery): The storage then does not feed this appliance; it runs on solar power or grid.

## Safety and emergency stop

A storage in external mode keeps working with the **last setpoint**, even if nobody is controlling it any more. SOLASI protects against this in several layers:

1. **Not-Aus button (⛔) at the top** (*Not-Aus* = emergency stop). It stops SOLASI immediately. All storages go to 0 W and into the **fallback mode** (for example self-consumption). SOLASI then checks whether the mode was set and reports it if not.
   The button turns into **▶ Fortsetzen** (Resume). The stop persists even after a restart.
2. **Not-Aus switch in Home Assistant** (optional, *Sicherheit & Meldungen*, Safety & Alerts): If a chosen switch is "on", SOLASI stops; when it turns "off", SOLASI keeps running. This lets you stop SOLASI from automations or with a push button as well.
3. **Automatic stop** when the meter fails (preset to 5 minutes, until then the storages stay at 0 W) and when control commands fail repeatedly. If you wish, SOLASI then resumes on its own after 5 quiet minutes,
   otherwise it stays stopped until you press "Fortsetzen" (Resume).
4. **Release on shutdown:** If you stop, start or update the add-on, SOLASI releases the storages. The same applies when you switch off live control or switch to *Testmodus* (test mode).
5. **Watchdog for crashes.** If SOLASI suddenly fails completely, it cannot reset anything itself. That is why it sends a heartbeat every 30 seconds and creates the automation **"SOLASI Wächter"** (SOLASI watchdog) in Home Assistant.
   It runs independently: if the heartbeat is missing for longer than a set time (preset to 3 minutes), or if SOLASI does not report back after a restart of Home Assistant, it sets the storages to the fallback mode and sends an alert.
   If you stop SOLASI yourself, the watchdog does not intervene, because the storages are already released by then. SOLASI keeps the automation up to date. Changes you make to it by hand will be overwritten.
   If SOLASI is not allowed to create an automation, *Sicherheit & Meldungen* shows the finished text to paste in.

**Setting the fallback mode:** Enter it for each storage under *Einrichtung* (Setup) in the field "Beim Stoppen: Modus setzen auf" (When stopping: set mode to). Without it, the storage stays in external mode at 0 W.

**Want to switch briefly in the manufacturer's app?** Use the Not-Aus first, otherwise SOLASI will set the mode back after 30 seconds at the latest.

**Limits:** If Home Assistant itself is unreachable, SOLASI cannot send any commands. Observe the legal feed-in limits for your system.

## Notifications

Under *Einstellungen → Sicherheit & Meldungen* (Settings → Safety & Alerts) you choose a target, for example `notify.mobile_app_dein_handy` for a notification on your phone or `persistent_notification` for the bell in Home Assistant.
Alerts are sent for: meter not reporting, storage unreachable, storage empty, feed-in despite a full storage, failing control commands, and when SOLASI has been stopped.
An alert is only sent once the fault has lasted a configurable time, the same alert repeats at the earliest after a lock-out period, and an all-clear message follows when the problem is resolved. Use **Testnachricht senden** (Send test message) to check the target.

## Evaluation: Statistics and Replay

**Statistik** (Statistics): For each day you see consumption, solar yield, grid import, feed-in and storage throughput, plus **Autarkie** (self-sufficiency), **Eigenverbrauch** (self-consumption) and amounts based on your prices (*Sicherheit & Meldungen → Preise*, Safety & Alerts → Prices).
The values are approximations. To calculate household consumption, SOLASI needs sensors for charging and discharging (or a household consumption sensor).

**Replay:** *Auswertung → Replay* (Evaluation → Replay) runs real historical data from the last few hours (up to 72) through the control logic. You can change individual settings and see grid import, feed-in, state of charge, Eco time and
switching operations compared with the measured values and with your current settings. The prerequisites are a grid sensor and, for each storage, state of charge, charge and discharge power and PV power, as well as an active recorder.
The replay is an **approximation**. The "Modell-Check" (model check) shows how far the simulation with your settings deviates from what was measured. With the assumption "Firmware drosselt PV bei vollem Speicher" (firmware throttles PV when the storage is full) you can play through both possibilities.

## Self-Test and Energy Balance

**System → Selbsttest** (System → Self-test) shows:

- **Systemprüfung** (system check): It checks all selected entities (do they exist, do they deliver numbers, is the unit correct, are the required options available) and gives a solution for every problem. It also checks the fallback mode, the Not-Aus (emergency stop) switch and notifications.
- **Energiebilanz** (energy balance): Solar, battery, output to the house, grid and house, calculated from your sensors. **Compare these values with the manufacturer's app.** If they differ, the sensor selection or the **Messart** (measurement type) is usually wrong.
  A warning also appears if charging sensors look more like battery power than grid power.
- **Abregelung bei vollem Speicher** (curtailment when the storage is full): When storages are full and the sun is shining, SOLASI watches whether power is still being fed in. After three minutes of feed-in, curtailment is considered *nicht wirksam* (not effective); consumers may then run earlier
  and you receive an alert. If the meter stays balanced, it is considered *bestätigt* (confirmed).

## Meters and Daily Consumption

Under *Betrieb → Zähler* (Operation → Meters) you show further meters from Home Assistant in SOLASI and in the dashboard card, for example **Zählerstand Strom** (electricity meter reading, kWh) or **Wasserzähler** (water meter, m³). The row sits at the very top, separate from the energy flow.

- **Tagesverbrauch** (daily consumption): the large tile shows what the house has consumed today. It can be switched off.
- **Zähler hinzufügen** (add meter): choose the sensor, then specify name, icon and color. Up to eight meters are possible. Sensors that only count upward are suitable. SOLASI takes the unit and decimal places from the sensor.
- **Verbrauch heute** (consumption today): for each meter you can display the difference from the start of the day, for example "+0,18 kWh heute" (+0.18 kWh today). **Wasserzähler** (water meters; unit m³, water-drop icon or "Wasser" in the name) show today's consumption in **liters** ("+180 l heute"); the meter reading stays in m³. For this, SOLASI remembers the first value of the day. On the first start in the middle of a day, consumption is counted from that point on. If a meter is replaced or reset, counting starts over.
- **Solarertrag und Netzbezug heute** (solar yield and grid import today) can be added as further tiles.
- **Reihenfolge** (order): on the same page you arrange all tiles with arrows. The card adopts this order; with `meters_order` (e.g. `[day, "m:sensor.wasser", pv, imp]`) a card gets its own order, set with arrows in the editor. If the daily consumption is in first place, it is shown large; otherwise all tiles are the same size.

## Statistics of a Tile

Tap a tile in the overview (daily consumption, meter, solar yield, grid import) to see its history: bars per day for 7, 30 or 90 days, plus total, average and highest day. For meters, SOLASI reads the daily values from Home Assistant's long-term statistics; if the sensor has none (it needs `state_class: total_increasing`), the recorder history is evaluated instead. Water meters show liters. In the dashboard card, tapping a meter tile instead opens the meter's history and statistics in Home Assistant.

## Arranging Blocks

Under *Einstellungen → Darstellung → Anordnung* (Settings → Appearance → Arrangement) you set the order of the blocks in **Übersicht** (Overview: key figures, meters, energy flow, trend, storage, surplus, log) and **Statistik** (Statistics: period, key figures, chart). Use the arrows to move a block and the checkbox to hide it. The arrangement is stored with *Speichern* (Save) and applies on all devices. *Standard wiederherstellen* (Restore default) resets it. If the page jumps on its own while scrolling: switch on *Einstellungen → Darstellung → Sprung-Diagnose* (jump diagnostics); the bottom left then shows what is shifting.

On wide screens SOLASI distributes the blocks over two columns in the chosen order; on a phone they are stacked.

## Dashboard Card

On startup, SOLASI installs the card `solasi-card` and registers it as a dashboard resource. Under **System → Dashboard-Karte** (System → Dashboard card) you see the status and, if needed, find the manual instructions.

All options can also be set in the visual editor, with the order of the blocks set via arrows below the switches. A block that is not listed in `order` is appended at the end in the default order; hiding is still done with the `show_*` options. The Not-Aus (emergency stop) button only appears if the switch *Not-Aus* exists, that is, with MQTT.

Add the card: edit the dashboard → *Karte hinzufügen* (Add card) → choose **SOLASI**, or "Manuell" (manual):

```yaml
type: custom:solasi-card
entity: sensor.solasi        # optional
title: SOLASI                # optional, "" hides the title
show_headline: true          # plain-text headline
show_batteries: true         # state of charge per storage
show_surplus: true           # surplus and consumers
show_tags: true              # Eco, meters, setpoint
size: large                  # large or compact (four tiles, no chart)
show_meters: true            # row with daily consumption and meters at the very top
meters_layout: big           # big (large tile on the left) or even (all the same size)
meters_order: []              # order of the meter tiles, empty = as in the add-on
order: [meters, headline, flow, trend, batteries, surplus, tags]   # order of the blocks (default as here)
show_trend: true             # trend of the last 24 hours
show_kill: true              # Not-Aus button with confirmation prompt (requires MQTT)
tap_open: true               # tapping opens SOLASI
accent: ""                   # accent color, e.g. "#3F5BD8"
```

**Entities for your own cards, histories and automations:** `sensor.solasi` (status, all values as attributes), `sensor.solasi_pv_power`, `sensor.solasi_house_power`, `sensor.solasi_battery_power`
(+ discharging, − charging), `sensor.solasi_target_power`, `sensor.solasi_surplus_power`, `sensor.solasi_base_load`. With an MQTT broker, SOLASI replaces them with permanent entities (see below); without a broker they are simple sensors that are recreated immediately after a Home Assistant restart.

**Automatic installation not working?** Copy `solasi-card.js` to `/config/www/solasi/` and, under *Einstellungen → Dashboards → ⋮ → Ressourcen* (Settings → Dashboards → ⋮ → Resources), add the URL `/local/solasi/solasi-card.js` as a JavaScript module
(to do this, enable advanced mode in your user profile). If the `www` folder was newly created, restart Home Assistant once.

## Permanent Entities and Energy Dashboard (MQTT)

With an MQTT broker (the easiest option is the **Mosquitto broker** add-on), SOLASI creates real entities in Home Assistant. They survive a restart, appear in the entity registry, have a history and can be used in the **Energy dashboard**.

**Setup:** Install and start the Mosquitto add-on, confirm the MQTT integration, restart SOLASI. Nothing more is needed; SOLASI finds the broker by itself. Under **System → Entitäten (MQTT)** (System → Entities (MQTT)) you can see whether the connection is up. You can also enter your own broker there.

All entities belong to the device **SOLASI** (*Einstellungen → Geräte & Dienste → MQTT*, Settings → Devices & Services → MQTT):

| Type | Entities |
|---|---|
| Power (W) | Solar power, house consumption, storage power (+ discharging, − charging), grid power (+ import), setpoint, surplus, base load (learned) |
| State of charge | Average of all storages (%) |
| Energy counters (kWh) | Solar yield, house consumption, grid import, feed-in, storage charged, storage discharged. They keep counting permanently and fit directly into the Energy dashboard |
| Switches | **Regelung** (control), **Testmodus** (test mode), **Not-Aus** (emergency stop). With these you can also switch SOLASI from automations, scenes and voice assistants |
| Notices | State, meter problem, Eco mode active |

*Energy dashboard:* Under *Einstellungen → Dashboards → Energie* (Settings → Dashboards → Energy) you can link grid import, feed-in, solar yield and the storage (charged/discharged) to these counters. The counters start at 0 as soon as SOLASI delivers them for the first time.

**Without MQTT** SOLASI keeps working unchanged: the card, the watchdog and all functions run, and the values are available as simple sensors (`sensor.solasi_pv_power` etc.). These sensors are not in the entity registry and are briefly missing after a Home Assistant restart. As soon as MQTT is connected, they are replaced by the permanent entities.

**Not-Aus as a switch:** *An* (On) stops SOLASI and releases the storages, *Aus* (Off) resumes control. The state is preserved even after a restart.

## Backing Up the Settings

Under *Einstellungen → Sicherheit & Meldungen → Sicherung der Einstellungen* (Settings → Safety & Alerts → Settings backup) you download all settings as a file and restore them when needed, for example for a new installation.
The settings are also part of the Home Assistant backups.

## FAQ and Troubleshooting

**Can I try out SOLASI without anything happening?**
Yes, with the **Testmodus** (test mode). SOLASI then calculates everything and writes to the log what it would send, but sends nothing.

**How do I stop SOLASI quickly?**
With the **⛔ Not-Aus** (emergency stop) at the top. The storage goes to 0 W and into fallback mode. With **▶ Fortsetzen** (Resume) SOLASI carries on.

**The storage shows "Leistung nicht verfügbar" (power not available).**
This is normal as long as it is not in external control mode. As soon as SOLASI controls it live, it switches it over. In test mode the state stays as it is.

**SOLASI is not regulating, the setpoint stays at 0 W.**
Check in order: Is **Regelung** (control) switched on? Is the **Testmodus** still on? Does it say **Gestoppt** (stopped) at the top? Is the grid import below the switch-on threshold (default 120 W)?
Is the state of charge below the minimum, or is Eco mode in effect? The **Selbsttest** (self-test) shows errors in the setup.

**"Solar" shows "–".**
The selected PV sensor is currently delivering no value or was chosen wrongly. Compare with the manufacturer's app in the device's sensor list.

**House consumption or storage power differ from the manufacturer's app.**
Open *System → Selbsttest → Energiebilanz* (System → Self-test → Energy balance) and check the sensor selection and the **Messart** (measurement type). Small deviations occur because meters and storages measure at different intervals.

**The mode keeps jumping back in the manufacturer's app.**
This is intentional: SOLASI keeps the storage in external control mode. To change it, use the **Not-Aus** beforehand, or switch off "Externe Steuerung automatisch einschalten" (switch on external control automatically) under *Regelung → Funktionen* (Control → Functions).

**What happens when Home Assistant or SOLASI restarts?**
SOLASI carries on afterwards. An Not-Aus that was set remains in place. When shutting down, SOLASI releases the storages; in the event of a sudden crash, the watchdog takes over.

**Can I mix storages from different manufacturers?**
Yes, each storage has its own type. SOLASI distributes the setpoint across both.

**After an update the interface looks old.**
Reload the page (`Ctrl + Shift + R`, on a Mac `Cmd + Shift + R`).

**Where is my data stored?**
Settings, statistics and learned values are stored in the add-on's data folder and are part of the Home Assistant backups.

**I found a bug or have an idea.**
Get in touch at [github.com/DEIN-NAME/solasi/issues](https://github.com/DEIN-NAME/solasi/issues/new/choose). Please attach the self-test and the log, but no credentials.

## Privacy and Liability

SOLASI runs locally and talks only to your Home Assistant. There is no cloud, no account and no data transfer to third parties.

The software controls hardware and is provided **without warranty**. You use it at your own risk. Observe your system's feed-in limits, registration obligations and your grid operator's requirements, as well as your storage manufacturer's instructions.
SOLASI is an independent project and is not affiliated with SolarAssistant (solar-assistant.io), Anker or any other manufacturers.

**Storage in maintenance or disabled:** If something on the system is to be modified, set the storage under *Einrichtung* (Setup) at "Betrieb" (operation) to **Wartung** (maintenance; greyed out, not controlled and not checked) or **Deaktiviert** (disabled; hidden, ignored). The same works via the Home Assistant entity "… Betrieb". SOLASI hands the storage back to its own control behavior in the process (the fallback mode must be entered for this). If a storage's state of charge does not respond for 2 minutes, it automatically goes into maintenance and comes back by itself (*Sicherheit → Nicht erreichbare Speicher automatisch in Wartung*, Safety → Automatically put unreachable storages into maintenance).

**Comparison with yesterday:** Under *Zähler* (Meters) you set whether the today tiles show a line with yesterday: up to the same time of day, whole day, or off. In the card, `meters_compare` (auto, same, full, off) overrides this. On the first day after installation, yesterday's hourly readings are missing, so the whole day or nothing is shown there.

**Setting the dashboard card in the add-on:** *Einstellungen → Darstellung → Dashboard-Karte* (Settings → Appearance → Dashboard card) applies to all cards. Options in the card itself (YAML) take precedence. The energy flow has its own group there with size (`flow_size`), template, tiles and order. On wide displays the energy flow grows with the display and spaces the tiles further apart.



## New in 2.0

**Modi** (modes): At the top of the overview you switch with one tap between Ausgewogen (balanced), Autark (self-sufficient), Akku schonen (protect battery), Urlaub (vacation) and Notfall (emergency). Under Einstellungen → Ziele (Settings → Goals) you set your own sliders; the calculated values are shown there in a table and you can change each one by hand.

**Automatik** (automation): Under Betrieb → Automatik (Operation → Automation) you create rules. Notifications go to the service from Sicherheit & Meldungen (Safety & Alerts). The weekly report arrives on Mondays at 8 a.m.

**Konten und eigener Port** (accounts and own port): Under Einstellungen → Konten & Zugang (Settings → Accounts & Access) you create accounts. To open SOLASI without Home Assistant, enter a port at "8100/tcp" under Netzwerk (Network) in the add-on configuration. Without an account the port is open (anyone on the network may operate everything); as soon as you create an account, it requires a login. Use it only on your home network.

**Klassische Ansicht** (classic view): If you want the old menu navigation, switch it on under Einstellungen → Ansicht (Settings → View).

**Modi:** The active mode is shown at the top in the header and on the dashboard card. Under Einstellungen → Ziele, "So arbeitet SOLASI" (How SOLASI works) explains what each mode does (a table with the calculated values and the formulas). Modes only set limits: discharge down to X %, charge up to Y %. SOLASI never actively charges from the grid, only from surplus.

**Haus-Ansicht** (house view): Einstellungen → Darstellung → Ansicht (Settings → Appearance → View) "Haus in Schrägansicht" (house in oblique view). The first solar array sits on the house roof, further ones stand in front of the house; storages are cabinets in front of the house. It works for up to four storages.

**Laden aus dem Netz** (charging from the grid): Under Betrieb → Laden (Operation → Charging) you set the target, total power, storages and order, and start the job. SOLASI then charges at the storages' "max. Laden" (max. charging) power (limited by your total power and, if a fuse is entered under Phasen, by the feed-in phase), raises the charge ceiling for this purpose, and ends the job at the target, after the maximum duration, on Not-Aus, or if the state of charge does not rise for 20 minutes. Afterwards the normal mode applies again. The electricity comes from the grid and costs money. The same action exists in Automatik ("lade die Akkus aus dem Netz", charge the batteries from the grid). There is no price sensor / dynamic tariff yet.

**Local update (beta):** Under System → *Update (Beta)* (visible in expert mode) you upload the repo zip and SOLASI installs it without you having to publish it on GitHub. SOLASI checks the file, unpacks the code into its data folder and restarts. If the new version crashes within the first minute, SOLASI automatically falls back to the version shipped with the add-on; with the buttons at the bottom of the page you can also go back manually or restore the previous version. The version number in the zip must be higher than the one installed in the add-on. `config.yaml`, the Dockerfile and Python packages cannot be replaced this way - that needs a normal add-on update. Installing is possible only through the Home Assistant interface, not through the direct port. Anyone who can upload code fully controls SOLASI; only upload files you trust.

**Entladesperre** (discharge lock): Under Betrieb → Laden you lock individual storages against discharging (until a time of day or until released). The solar power from the modules still goes to the house; nothing comes from the battery. For the Laden job (charging job) you can also specify that no discharging takes place during it and that the storages stay locked afterwards. The power in the job refers to the grid share; with Anker, solar charging is added on top.

**Phasen** (phases): Under Betrieb → Phasen (Operation → Phases) you switch on the analysis and assign its sensors to each phase ("Vorschläge übernehmen", accept suggestions, guesses the assignment from the names). SOLASI shows power per phase, phase imbalance (Schieflast) and, if you enter your fuse, the utilization. SOLASI detects the feed-in phase passively: it compares on which phase the grid import drops when the storages output more. This requires a number of power changes (about 12), which happens in normal operation. In case of errors you can set the phase by hand.

**Stromfresser** (power hogs): Under Auswertung → Stromfresser (Evaluation → Power hogs) you enter metering sockets (Shelly, LSC …) via their power sensor. From then on SOLASI records every 10 seconds (10-s values for 48 hours, minute values for 90 days) and shows a ranking with kWh, share of the house, €/year and standby; the remainder is "nicht gemessen" (not measured). Filters: period, time of day (also across midnight) and weekdays. The power curve is available in 10 s, 1 min and 15 min, with comparison to yesterday. There is no data retroactively. If a device is removed, its recordings are deleted.
