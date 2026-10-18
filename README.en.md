<p align="center"><img src="solasi/logo.png" alt="SOLASI" width="250"></p>

# SOLASI – Zero Feed-in and Energy Control for Home Batteries

🇩🇪 [Deutsche Version](README.md)

The user interface is currently available in German only.

> **🧪 Beta:** SOLASI is still in beta. It was developed and tested in everyday use on a system with Anker SOLIX (Solarbank 4); other storage types are implemented according to the descriptions of their integrations and have so far only been checked in simulations. It controls real hardware, so errors are possible. Always start in **Testmodus** (test mode), keep the **Not-Aus** (emergency stop) in view, and try new functions (for example grid charging and discharge lock) with short tests first. Use at your own risk. Feedback and bug reports are welcome.

SOLASI is an add-on for **Home Assistant**. It controls your battery storage so that your house uses as much as possible of the electricity your
solar system produces: hardly any feed-in to the grid, hardly any draw from the grid. Everything runs **locally** on your Home Assistant, with no cloud and no account.

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDEIN-NAME%2Fsolasi)

## What SOLASI can do

- **Zero feed-in:** One or two batteries are controlled together so that the grid meter stays close to zero.
- **Solar power goes to the house first:** Even when the battery is empty, solar power goes straight to the house without discharging the battery.
- **Eco mode:** Protects the battery at a low charge level and, if you like, learns your house's nightly base load.
- **Use surplus:** A heating element, wall box (continuously variable) or any switches run when there is more solar power than the house needs.
- **Multiple storage types:** Anker SOLIX, Marstek and others, plus inverter limits and a custom script for everything else. Types can be mixed.
- **Live overview:** Energy flow with solar, battery, house and grid (with two systems, each with its own battery), total charge level in kWh and a card for your dashboard.
- **Fixed entities (MQTT):** Sensors, energy counters for the Energy dashboard and switches for control, *Testmodus* (test mode) and *Not-Aus* (emergency stop).
- **Evaluation:** Daily statistics with self-sufficiency, savings and the energy from the batteries, plus a "what if" replay (*Was wäre wenn*) using your real history data.
- **Safety:** *Testmodus*, an *Not-Aus* button, automatic fallback to the manufacturer's own mode (e.g. self-consumption), a watchdog that steps in
  on a failure, notifications to your phone and a self-test that checks your setup.

## Requirements

- **Home Assistant OS or Supervised** (you have an add-on store). Home Assistant Container and Core do not support add-ons.
- A **battery with Home Assistant integration**; for Anker, the official integration [Anker Solix Official](https://github.com/anker-charging/ha-anker-solix-official).
- A **sensor for grid power in watts**, e.g. a reading head on the electricity meter or a Shelly EM (positive = draw, negative = feed-in).
- Recommended: a **sensor for solar power** for each battery.

## Installation

1. In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories** and add this address:
   `https://github.com/DEIN-NAME/solasi` (or use the button above).
2. Open **SOLASI**, click **Install** and **Start**, then turn on **Show in sidebar**.
3. Open SOLASI in the sidebar. The *Willkommensseite* (welcome page) guides you through the setup.

## Getting started

1. **Select meter and battery** (*Einrichtung*, setup). The self-test (*Selbsttest*) under *System* shows whether everything fits.
2. **Leave *Testmodus* on** and switch **Regelung** (control) on. SOLASI then calculates everything but sends nothing. In the *Protokoll* (log) you can see what would happen.
3. Once the values look plausible, **switch *Testmodus* off**. From now on SOLASI controls your battery.
4. Get familiar with the **Not-Aus** beforehand: one click stops SOLASI and returns the battery to its own mode.

The detailed guide is in the [documentation](solasi/DOCS.en.md), which you can also find in the add-on under **Documentation**.

## Supported batteries

| Battery | Connection | Status |
|---|---|---|
| Anker SOLIX Solarbank 4 E5000 Pro (also two) | Anker Solix Official | tested in everyday use |
| Marstek (e.g. Venus), batteries with a signed power value or with mode and power values | matching Home Assistant integration | implemented according to manufacturer description, so far only tested in simulations |
| Inverters with power limiting (e.g. via OpenDTU) | number for output | as above |
| All others (e.g. Victron, Huawei, Sungrow) | custom script | as above |

For everything except Anker, please **observe in *Testmodus* first** and feel free to send feedback.

## Frequently asked questions

**My battery no longer delivers anything, even though the charge level is still above 0 %.**
Most batteries have their own discharge limit (adjustable in the app for Anker) below which they deliver nothing. SOLASI cannot override this limit.
Enter the "Entladegrenze" (discharge limit) entity of your battery under *Einrichtung*, and SOLASI will automatically follow it. If SOLASI notices that a battery delivers nothing despite being asked to,
it shows "Grenze" (limit) and stops querying it for a while, until its charge level changes.

**Why does the heading say "Das Netz versorgt dein Haus" (the grid supplies your house) even though SOLASI is requesting discharge?**
The heading shows what is actually flowing, not what SOLASI requests. If the battery is currently delivering nothing (for example at its discharge limit), you see that immediately.

**What happens when the battery is full?**
Depending on the device, the battery only passes solar power through and does not follow software commands. The self-test under *System*
("Abregelung bei vollem Speicher", curtailment when the battery is full) shows whether power is still fed in.

**How do I get the menu on my phone?**
The bar with *Übersicht* (overview), *Speicher* (battery), *Statistik* (statistics), *Überschuss* (surplus) and "Mehr" (more) is at the top. Under "Mehr" you find everything else.

**How do I stop SOLASI immediately?**
With the **Not-Aus** at the top right. The battery then returns to its own mode. "Fortsetzen" (resume) hands control back to SOLASI.

## Important notes

- **Always test in *Testmodus* first.** SOLASI controls real hardware.
- **Observe the feed-in limits** of your system (e.g. 800 VA for plug-in solar devices) and your grid operator's requirements. The default for total output is deliberately cautious.
- **Use at your own risk.** The software is provided without warranty (see [License](LICENSE)).
- **Privacy:** SOLASI only talks to your Home Assistant. No data is sent to third parties.

## Help and feedback

- Under **System → Selbsttest**, open the system check; it lists errors in your setup with a suggested solution.
- The *Protokoll* under *System* shows what SOLASI has done.
- If you find a bug or have an idea, [get in touch here](https://github.com/DEIN-NAME/solasi/issues/new/choose). Please attach the self-test and log, but no credentials.

## About the project

**SOLASI** stands for **SOL**ar-**A**nlagen-**S**peicher-**I**nterface (solar system storage interface). The project is independent and not affiliated with *SolarAssistant*, Anker or other manufacturers.
The control strategy is based on the forum blueprint "Anker SOLIX 4 Pro – Lokale Nulleinspeisung & Eco-Modus" by MBP996 in the Home Assistant forum; the code is an original implementation.
Free software under the [MIT License](LICENSE).
