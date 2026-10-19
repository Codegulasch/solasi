# Changelog

🇩🇪 [Deutsche Version](CHANGELOG.md)

## 2.4.0
- **Local update (beta):** Under System → *Update (Beta)* (expert mode only) you upload the repo zip without publishing it on GitHub. SOLASI checks the file (structure, file types, syntax, a trial import of all modules in a separate process), installs the code into its data folder and restarts. SOLASI keeps the previous version as a fallback.
- **Safety net:** A new launcher (`boot.py`) starts SOLASI from the local version. If a freshly installed version crashes within the first minute, SOLASI immediately falls back to the version shipped with the add-on, and the interface shows what happened. If a real add-on update with the same or a higher version arrives, the local version is discarded.
- **Access:** Installing is possible only for the owner through the Home Assistant interface, not through the direct port.
- **Limits:** `config.yaml`, the Dockerfile and Python packages cannot be changed this way. **This version has to be installed once the normal way** (launcher and Dockerfile change); after that, uploads work.

## 2.3.2
- **Fix for Entladesperre** (discharge lock): The time could not be entered because the field was redrawn on every refresh. It is now preserved.
- **Dashboard-Karte** (dashboard card): "Tap opens SOLASI" keeps trying to retrieve the add-on name if the start failed, and the "Dashboard-Karte" page shows whether the path is ready. New: a "Pfad zum Öffnen" (path to open) field in the card (e.g. `/hassio/ingress/<add-on-name>`) as a fallback.
- **Beta notice** in the README, the guide, the interface and the add-on description (add-on stage "experimental").
- **English documentation:** The README, guide, changelog and development notes are now also available in English.

## 2.3.1
- **Discharge lock per storage unit:** Under Betrieb (Operation) → **Laden** (Charging), each storage unit can be locked individually, even without a charging job, until a given time or until released. While locked, the storage unit delivers nothing from the battery; whatever the modules are producing at the moment still goes to the house. Shown in the header and on the dashboard card; locks survive a restart.
- **With a charging job:** "Währenddessen nicht entladen" (do not discharge in the meantime; on by default) and "Danach halten" (hold afterwards: carry on normally, lock until a given time or until released), so that the charge is kept for tomorrow.
- The power in the job is the share from the grid: with Anker, solar power goes into the battery in addition.

## 2.3.0
- **Charging from the grid:** New page "Laden" under Betrieb. Set the target in %, the power (total), the storage selection and the order, then press "Laden starten" (start charging). SOLASI charges the storage units even while drawing from the grid until the target is reached, and then stops by itself. Includes an estimate (kWh, duration), progress per storage unit, and display in the header and on the dashboard card.
- **Configurable order:** lowest charge level first, highest first, as in the storage list, or all at the same time; default under "Laden", overridable per job. Plus a maximum total power.
- **Protection:** The charge upper limit in the storage unit is raised for the job and reset afterwards. If the fuse is entered under Phasen (phases), the charging power is limited so that the feed-in phase is not overloaded. The job ends on Not-Aus (emergency stop), after the chosen maximum duration, or if the charge level does not rise for 20 minutes (with a message).
- **Automatik** (automation): New action "charge the batteries from the grid" (target, power, storage units), e.g. at 02:00 at night up to 80 %.
- Not included: price window / dynamic tariff – coming as soon as you have one.

## 2.2.2
- **Fix:** SOLASI did not start after the update to 2.2.1 if a learning file from the phase detection of 2.2.0 already existed. Old or damaged files are now ignored, and the detection then starts over.

## 2.2.1
- **Phasen display:** The bars now show the load on the fuse (green up to 70 %, yellow above that, red from your warning threshold) and only deflect that far. If no fuse is entered, 16 A is assumed.
- **Phases in the energy flow and on the card:** Below the flow there is a strip with L1–L3 (watts, amperes, load, ⚡ which storage unit feeds in on that phase). Can be switched off under Darstellung (Appearance).
- **Feed-in phase per storage unit:** SOLASI now learns separately for each storage unit which phase it feeds into, even if the storage units feed into different phases. Can be set manually per storage unit.
- **Sensor suggestions:** Phases are recognized from more name patterns (Phase A, Channel C, Kanal 3, L3, `…_phase_c_active_power`).
- **Mode buttons** are more subtle. The link "So arbeitet SOLASI" (How SOLASI works) now opens the explanation (the same applies to other links in the text, e.g. in the Automatik).

## 2.2.0
- **House view:** Under Einstellungen (Settings) → Darstellung, the energy flow can be shown as a house in an angled view (also applies to the dashboard card). The house carries the first solar array on its roof, further arrays stand on mounting frames in front of the house; each storage unit is a cabinet with its charge level, the grid is a pylon. The flow runs as evenly moving dots along the paths, with the watt value for each path.
- **Phasen (3-phase meter):** New page under Betrieb. Power, voltage and current per phase (e.g. Shelly 3EM), unbalanced load, fuse load with warning. The total meter remains unchanged.
- **Feed-in phase is detected:** SOLASI compares the power steps of the storage units with the changes per phase and shows which phase is being fed into (with confidence in %). Can be set manually; "Neu messen" (measure again) starts over.

## 2.1.0
- **Modes visible and explained:** The active mode is shown in the header and as a tag on the dashboard card. The overview shows the "Wirkung" (effect) (Delivers down to X %, charges up to Y %, per storage unit). New: "So arbeitet SOLASI" under Ziele (Goals) with a table of all modes and the formulas.
- **Stromfresser** (power hogs): New page under Auswertung (Analysis). Records measuring sockets (10 s / 1 min), ranking with kWh, share, €/year, standby and "nicht gemessen" (not measured), filters by period, time of day and weekdays, power curve with comparison to yesterday. Optionally a phase per device (preparation for 3-phase).
- **Removed:** Search (Ctrl+K) and demo mode.
- **Fix:** Tiles in "Heute und Zähler" (Today and meters) no longer wrap in the middle of a word at narrow widths.

## 2.0.1
- **Fix:** On the overview, the key-figure tiles overlapped the card below (the spacing was lost). The spacing is back.
- **Own port, as with PrintDock:** Without an account the port is open (everyone on the network counts as owner). As soon as the first account exists, it requires a login. The accounts page points this out as long as the port is open.
- **Demo mode:** Under Einstellungen → Ansicht (View) (and on the start page before setup), SOLASI can be viewed with simulated values. While demo is on, SOLASI controls nothing.
- Search: Answers from the log now display the time correctly.

## 2.0.0
- **New interface:** Menu in Betrieb / Auswertung / System, settings as an overview with topics, a change bar with "Verwerfen" (Discard). Energy flow, statistics and all previous pages remain. Under Einstellungen → Ansicht there is "Klassische Ansicht" (classic view) as a way back.
- **Modes and goals:** five modes for quick selection (Ausgewogen (Balanced), Autark (Self-sufficient), Akku schonen (Protect battery), Urlaub (Vacation), Notfall (Emergency)) plus custom modes. Three sliders (Reserve, Genauigkeit (Accuracy), Akku schonen) calculate the individual values; every individual value can still be changed by hand and is then marked as "angepasst" (adjusted).
- **Storage:** list on the left, settings per storage unit in tabs (Verbindung (Connection), Grenzen (Limits), Leistung (Power), Umladen (Transfer), Erweitert (Advanced)), Aktiv/Wartung/Aus (Active/Maintenance/Off). Up to four storage units; the distribution now also works with more than two.
- **Device detection:** "Speicher hinzufügen" (add storage) searches Home Assistant for matching devices and pre-fills the fields (or fill them in by hand).
- **Gesundheit** (Health): to-do list with "Beheben" (Fix) buttons that jump directly to the right setting.
- **Search (Ctrl+K):** pages, modes, commands ("Reserve auf 40 %") and questions that are answered from the log.
- **Automatik:** schedules and if-then rules (time, charge level, grid draw, solar power → switch mode or send a notification) and a weekly report by notification.
- **Accounts and own port:** accounts with roles (Besitzer (Owner), Mitbewohner (Housemate), Nur lesen (Read only)), passwords stored with scrypt, lockout after failed attempts. Direct access on port 8100 is off by default (enter a port in the add-on under Netzwerk (Network)) and always requires a login.
- Transfer between storage units is noted in the log ("A delivers – B charges … W").

## 1.7.2
- **Transfer as "durchgereicht" (passed through):** If one storage unit charges the other via AC, this power is included in the measured house consumption. Now the house tile shows the real consumption ("+340 W Laden"), the line to the charging storage unit carries "durchgereicht", and the headline says "durchgereicht, kein Mehrverbrauch" (passed through, no extra consumption). Daily consumption, comparison with yesterday, self-sufficiency and the base-load learning function also subtract the passed-through power (from this update on). Below 10 W nothing is displayed. Can be switched off under *Darstellung → Energiefluss* (Energy flow), in the card with `flow_passthrough: false`.
- **Total solar in the energy flow:** The lines now leave the "Solar gesamt" (total solar) tile sideways to the left and right and run into the arrays from above. This gives a rounder overall picture.

## 1.7.1
- **Transfer surplus into another storage unit:** If a storage unit is full and another can charge via AC (switch "Laden aus dem Netz" (charging from the grid) on, power-flow option "Netz-zu-Batterie-Ladeleistung" (grid-to-battery charging power)), SOLASI no longer throttles the full one. Its solar power goes to the house, the rest is fed into the grid, and the other storage unit charges this surplus as soon as it is above the switch-on threshold. The headline then reads "Überschuss von HÜTTE lädt DACH mit 340 W" (surplus from HÜTTE charges DACH with 340 W), and in the energy flow the line runs from the house to the charging storage unit. If all storage units are full, throttling happens as before. Can be switched off under *Funktionen → Überschuss in anderen Speicher umladen* (Functions → transfer surplus into another storage unit). Note: about 10–15 % is lost when transferring via inverter and grid connection.
- **Emergency power reserve:** New optional entity per storage unit (read only). SOLASI treats it like the discharge limit: the minimum charge level is the highest of its own minimum, the discharge limit and the emergency power reserve. The self-test displays it.
- **Power limits automatic:** If the power control has the attributes `max_charge_power` and `max_discharge_power` (Anker), SOLASI reads the limits from them when no entity of its own is entered.

## 1.7.0
- **Storage unit active, in maintenance or deactivated:** New per storage unit (*Einrichtung → Betrieb* (Setup → Operation)) and as the Home Assistant entity "… Betrieb" (Aktiv, Wartung, Deaktiviert). **Wartung** (maintenance) greys the storage unit out in the energy flow; SOLASI does not control, read or check it and reports no errors. **Deaktiviert** (deactivated) hides it as if it did not exist. On switching, SOLASI hands the storage unit back to its own control behavior (fallback mode); when switched back, it takes it over again immediately. The self-test skips such storage units.
- **Automatic maintenance:** If the charge level of a storage unit does not respond for 2 minutes (entity gone, renamed, unreachable), it goes into maintenance by itself instead of producing errors. When it comes back, it joins in again after 30 seconds. Can be switched off under *Sicherheit* (Safety).
- **Energy flow grows with the width:** On PC and tablet the drawing becomes wider and spreads the tiles apart; on a phone everything stays as before. New setting "Größe" (Size) (Automatisch (Automatic), Kompakt (Compact), Groß (Large)), `flow_size` in the card. The height limit of the drawing has been removed.
- **Gradient only behind the headline and energy flow:** As in the add-on overview, the gradient now sits on a block of its own, no longer behind the whole card.
- **Set up the card in the add-on:** *Einstellungen → Darstellung → Dashboard-Karte*: show and hide headline, meter row, daily curve, storage, surplus, notices, emergency-stop button and gradient; size, meter arrangement, accent color and order of the blocks. Applies to all cards. Options in the card itself take precedence; the card editor now only saves values that differ from the default.
- **Comparison with yesterday:** In the Today tiles (daily consumption, solar, grid draw, From storage and own meters) there is a line such as "gestern 5,8 kWh · ▲ 12 %" (yesterday 5.8 kWh · ▲ 12 %). By default the comparison is with yesterday **up to the same time of day** (SOLASI remembers hourly readings for this); until these are available, with the whole day. More solar is green, more grid draw red, the rest neutral. Configurable under *Zähler* (Meters) (Gleiche Uhrzeit (Same time of day), Ganzer Tag (Whole day), Aus (Off)), in the card with `meters_compare`.

## 1.6.0
- **Write limits into the storage unit:** New per storage unit (*Einrichtung*): "Eigener Mindest-Ladestand" (own minimum charge level), "Eigener Höchst-Ladestand" (own maximum charge level) (empty = global value) and the switch "Grenzen in den Speicher schreiben" (write limits into the storage unit). When it is on, SOLASI writes the minimum charge level into the discharge limit and the maximum charge level into the charge upper limit of the storage unit, and resets them if they change (also through the Anker app), at most every 5 minutes. Values are adjusted to the entity's minimum, maximum and step size; what was changed appears in the log. In Testmodus (test mode) only logging takes place; observed storage units are never written to. The self-test shows target and actual.
- **Energy flow with total solar at the top:** With two arrays, the solar power of all arrays, which is split between the two solar tiles, appears at the top center.
- **Energy flow configurable:** *Einstellungen → Darstellung → Energiefluss*: template (Gesamt-Solar oben (total solar on top), Paare (pairs), Kompakt (compact)), show and hide tiles individually (total solar, solar per array, storage, grid, house), grid in the middle or next to the house, order of the arrays. The card adopts this; with the options `flow_layout`, `flow_hide`, `flow_grid_pos` and `flow_order` (or in the card editor) it can be overridden per card. With more than two arrays, the order as well as grid and house apply.

## 1.5.1
- **Gradient in the dashboard card:** The card now has the same soft gradient as the overview in the add-on (accent color at the top left, fading into the card color). It follows the card option `accent` and adapts to light and dark mode. With `gradient: false` (or "Farbverlauf im Hintergrund" (gradient in the background) in the editor), the card stays a single color.

## 1.5.0
- **Headline shows what is really flowing:** Previously, for flows under 5 W it showed the target value ("The storage units supply your house with 339 W"), even though the grid was supplying the house. Now the text comes from the real flows. "Surplus charges …" only appears when really nothing comes from the grid; otherwise "Solar charges the storage unit with 80 W" and "House draws 511 W from the grid".
- **Storage tiles:** Instead of the same wattage twice, the tile shows "lädt" (charging) or "entlädt" (discharging), "bereit" (ready) when idle, "voll" (full) when the storage unit is full.
- **Discharge limit and charge upper limit:** New optional entities per storage unit (*Einrichtung*). SOLASI follows the storage unit's discharge limit (the higher value of the discharge limit and its own minimum charge level) and regards the storage unit as full from the charge upper limit. The self-test shows the effective values.
- **Storage unit that delivers nothing:** If a storage unit delivers nothing for about 90 seconds despite a request (for example at a limit in the device), it gets no share for the time being, the tile shows "Grenze" (limit), and the other storage unit takes over.
- **From storage today:** New tile in the Today row (under "Solarertrag, Netzbezug und Speicher heute dazu" (add solar yield, grid draw and storage today)), with the charged amount below it, tappable for the history. The daily chart in the statistics has a series "Aus Speichern" (From storage).
- **Menu on the phone:** The quick bar is now at the top (with statistics) and opens "Mehr" (More) from the top. At the bottom it disappeared behind the browser bar on some devices.
- **README** is now written purely for users, with frequently asked questions. Technical content is in DEVELOPMENT.md.

## 1.4.1
- **Energy flow with two arrays:** Each solar array now stands with its own storage unit as a pair (HÜTTE on the left, DACH on the right, grid and house in the middle). Each array has three lines: solar → own storage (charging power), solar → house and storage → house. Previously there was only one collective line "Solar → storage" that always ended at the first storage unit.
## 1.4.0
- **Total charge level by capacity:** The "mean charge level" is now weighted by the usable capacity of the storage units (previously a simple average) and is additionally shown in kWh ("6.2 of 15 kWh"). You enter the capacity per storage unit under *Einrichtung* (for example 5 and 10). Previously it was only in expert mode.
- **Energy flow with two arrays:** With two storage units, the energy flow shows each solar array and each storage unit as its own tile, with power, charge level and kWh. The design remains unchanged. With only one storage unit everything looks as before.
- **History:** An additional area "aus Speichern" (from storage) shows when the batteries delivered to the house (applies to add-on and card; the history fills up from now on, older points have no storage value).
- **Storage list and card:** Charge level per storage unit also in kWh.
- **Nur beobachten** (observe only): New option per storage unit. SOLASI reads charge level and power and displays them, but writes nothing to the storage unit and does not include it in its own target value. Intended for storage units that regulate themselves via their manufacturer app (for example Anker with smart meter and zero export).
## 1.3.5
- **Two storage units with different limits:** SOLASI now respects the maximum of the power entity (e.g. 800 W for the Anker Solix 4). Previously, with a higher discharge power setting (e.g. 1250 W), it requested more from the first storage unit than it accepts and did not distribute the remainder to the second.
## 1.3.4
- **Jumping, third round:** The card now keeps its `ha-card` element permanently and only swaps the content, so the card never stands empty for a frame. In addition, the card frame keeps its minimum height.
- **Version notice:** If the card file in the browser or the app is older than the add-on (cached), the card shows a notice "Karte veraltet – Seite neu laden" (card outdated – reload the page).
- **Jump diagnostics** of the card (option `debug: true`) shows the version and the latest events.
## 1.3.3
- **Jumping fixed (dashboard):** The cause could be narrowed down from a screen recording: the page became shorter for a moment, the browser clipped the scroll position and the view jumped to the top within one frame. There are now two safeguards. The card remembers its height per window width before the first drawing and no longer collapses, even if Home Assistant recreates it or the sensor briefly reports "unavailable" (the last state then stays dimmed). A **scroll guard** restores the old position if the page jumps to the top without input and ends up at the bottom.
## 1.3.2
- **Statistics per tile:** Tapping a tile in the overview opens a page of its own with history (7, 30 or 90 days), total, average and highest day. Meters fetch the daily values from Home Assistant's long-term statistics, alternatively from the recorder history; water is shown in liters. Daily consumption, solar yield and grid draw use the SOLASI statistics.
- **Card:** Tapping a meter tile opens the meter's history and statistics in Home Assistant; all other tiles continue to open SOLASI.
- **Against jumping:** every block of the overview never becomes lower than before (at the same width), so the page does not shrink and the browser does not shift the scroll position. The card reports its real height to Home Assistant (`getCardSize`) so that the dashboard layout does not shift afterwards.
- **Jump diagnostics:** can be switched on under *Einstellungen → Darstellung*. Fades in at the bottom left when the page jumps to the top without input or elements shift, and names the cause. Intended to track down a stubborn jump.
## 1.3.1
- **Arrange meter tiles:** under *Betrieb → Zähler → Reihenfolge der Kacheln* (order of the tiles) (daily consumption, each meter, solar yield, grid draw). The card uses the same order, or a custom one with `meters_order` (in the editor with arrows). If daily consumption is at the very top, it remains the large tile.
## 1.3.0
- **Arrange blocks:** *Einstellungen → Darstellung → Anordnung* (Arrangement) sets the order of the blocks in **Übersicht** (Overview) and **Statistik** (Statistics) (arrows, checkmarks to hide, "Standard wiederherstellen" (restore default)). The arrangement is saved in the add-on and applies on all devices.
- **Dashboard card:** new option `order` and arrows in the visual editor to move the blocks. Existing cards look unchanged; `show_*` continues to hide.
- **Water in liters:** the consumption today of all water meters (m³) is displayed as "+180 l heute" (today), in add-on and card. The meter reading stays in m³.
- **No more jumping:** the overview used to rebuild everything every 2 seconds, which made the page jump while scrolling, and opened *Technische Details* (technical details) collapsed again. Now only changed blocks are updated, the scroll position is compensated when heights change, and nothing is redrawn while scrolling. The card keeps its height (also while loading) and only redraws when the content has changed.

## 1.2.2
- **Meter row in the overview and dashboard card:** a row of its own at the very top, separate from the energy flow. It shows the **daily consumption** (house today) and any **meters** from Home Assistant, for example electricity meter reading or water meter.
  For each meter, the **consumption today** can be shown ("+0.18 m³ heute"). SOLASI remembers the reading at the start of the day for this. Optionally, solar yield and grid draw today are added.
- **New page *Betrieb → Zähler*:** sensor, name, icon and color per meter, up to eight meters, with preview.
- **Card:** new options `show_meters` and `meters_layout` (large tile on the left or all the same size), also in the visual editor.
- The meter row adapts to the width: in narrow cards the tiles are stacked.
- More spacing between the meter row and the energy flow.
## 1.2.1
- **New energy flow graphic** in the overview and in the dashboard card, both from the same code and therefore identical: tiles with their own icons (sun, battery with charge level, house, grid pylon), soft curves instead of angles, moving dots in the flow direction and lines that get thicker with the power.
- **History of the last 24 hours** (solar as an area, house as a line, current value as a dot) in the overview and in the card. The time axis now uses real clock times.
- **Headline from the energy flow:** e.g. "Solar supplies your house and charges the storage unit" instead of only following the target value.
- **Storage card** in plain language ("80 % charged · delivers 270 W", "Externally controlled"). The raw values are under *Technische Details*.
- **Log in the overview** is designed to be calmer.
## 1.2.0
- **New layout:** sidebar with the areas *Betrieb*, *Auswertung* and *System*, plus a top bar with status, **Regelung** (control), **Testmodus** and **Not-Aus** (with confirmation prompt). The design stays the same.
- **New overview:** key figures, energy flow, storage, surplus and log at a glance, plus a notice band when something needs attention.
- **On the phone:** bar at the bottom with the most important pages and a "Mehr" menu for the rest.
- **Settings** with their own navigation: *Regelung*, *Sicherheit & Meldungen* (Safety & notifications) and *Darstellung* (start page and density, remembered per device).
- **Setup wizard** in the new layout; on first start the sidebar is hidden. The steps *Solar* and *Haus* (House) are merged into **Solar und Haus**.
- **Dashboard card:** sizes *Groß* and *Kompakt*, daily curve of the last 24 hours, emergency-stop button with confirmation prompt (requires MQTT), tapping opens SOLASI, accent color and a visual editor.

## 1.1.0
- **Real entities via MQTT:** With an MQTT broker (e.g. the Mosquitto add-on), SOLASI creates a device "SOLASI" with fixed entities: power values, charge level, state, **energy counters for the Energy dashboard** and the switches **Regelung**, **Testmodus** and **Not-Aus**.
  The entities are retained after a restart and have a history. Without a broker everything works as before. New page *System → Entitäten (MQTT)* (Entities) and an entry in the self-test.
- Permanent total counters (kWh) for solar yield, consumption, grid draw, feed-in and storage.
- Note: The control accuracy was compared with various controllers in the simulator. The existing control is already close to the optimum, so it remains unchanged.
  A larger *Schrittweite* (step size) (e.g. 30 W) saves about a quarter of the write accesses to the storage unit at only about 3 % more deviation.

## 1.0.7
- **Not-Aus and release are more reliable:** When stopping, SOLASI now always sends 0 W and the fallback mode to the storage unit, even if the last known state already seems to match.
  Right after a command, the device often reports its new state with a delay. SOLASI could then have left the power in place even though the storage unit was still running. Applies to all storage types.

## 1.0.6
- New, detailed **guide** in Home Assistant (tab "Dokumentation" (Documentation)) with step-by-step setup, safety and troubleshooting.
- Revised short description in the add-on store.

## 1.0.5
- No changes to the app.

## 1.0.4
- **Switch on external control automatically:** As soon as SOLASI controls live, it sets the operating mode of the storage unit to external control (with Anker "third_party_control"),
  even if there is currently nothing to regulate. This happens at start, when live control is switched on, after "Fortsetzen" (Resume) and when the mode is changed from outside
  (then at most every 30 seconds). For storage units with a remote-control switch, this is switched on beforehand. In Testmodus, with "Regelung aus" (control off), in the Not-Aus state and during
  a meter failure, nothing is changed. Can be switched off under *Regelung → Funktionen*.

## 1.0.3
- **The energy flow shows where the solar power goes:** There is now a line of its own, *Solar → Speicher* (storage). Example: 780 W solar, storage charges 260 W, grid 9 W draw →
  520 W solar → house, 260 W solar → storage, 9 W grid → house. Each line carries its value. When charging from the grid, the charging power runs through the house into the storage unit.
  Applies to the interface and the dashboard card.

## 1.0.2
- **Fixed:** During first setup, the suggestions from "Beim Stoppen: Modus setzen auf" (When stopping: set mode to) onwards were missing. Now all sensors are available for selection immediately, and the device's sensors
  move to the front as soon as you type the power entity. The fallback options appear as soon as the operating mode is selected.

## 1.0.1
- **Solar power directly into the house, even with an empty storage unit:** If the charge level is below the minimum, the storage unit may deliver as much as its modules are currently producing.
  The battery is not discharged in the process. Can be switched off under *Regelung → Funktionen*.
- **Eco mode now only limits the share from the battery.** The solar power goes directly into the house in addition.
- **Measurement type of the power sensors (AC or battery):** For storage units with solar on the battery side (e.g. Anker), the house consumption is now calculated correctly.
- **Unknown is not 0:** If a sensor is unavailable, the overview and card show "–" instead of "0 W".
- **Sensor list per device** in the settings with current values for comparison with the manufacturer app.
- **Self-test:** new energy balance and a warning when charging sensors look like battery power instead of grid power.

## 1.0.0
First version.

- Zero feed-in for one or two home storage units with a shared controller, Eco mode, thresholds, charge level limits, charging from third-party surplus and throttling when the storage unit is full.
- Storage types: Anker SOLIX, signed number, mode + power values, output limit, custom script. Types can be mixed.
- Surplus control for up to three consumers, also continuously variable for wallbox and heating element.
- Safety: Not-Aus button, optional Not-Aus switch, automatic stop on meter failure or command errors, release of the storage units with fallback mode on stopping and exiting,
  automatically created watchdog in Home Assistant.
- Self-test, notifications, base-load learning, statistics and replay.
- Web interface with energy flow, expert switch and collapsible groups, dashboard card `solasi-card` and entities `sensor.solasi…`.
- Export and import of the settings.
