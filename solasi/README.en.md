# SOLASI

🇩🇪 [Deutsche Version](README.md)

The user interface is currently available in German only.

> **🧪 Beta:** SOLASI is still in beta. It was developed and tested in everyday use on a system with Anker SOLIX (Solarbank 4); other storage types are implemented according to the descriptions of their integrations and have so far only been checked in simulations. It controls real hardware, so errors are possible. Always start in **Testmodus** (test mode), keep the **Not-Aus** (emergency stop) in view, and try new functions (for example grid charging and discharge lock) with short tests first. Use at your own risk. Feedback and bug reports are welcome.

**Zero feed-in and energy control for home batteries, right in Home Assistant.**

SOLASI controls your battery storage so that your house consumes as much solar power itself as possible: hardly any feed-in to the grid, hardly any draw from the grid.
It runs locally on your Home Assistant, with no cloud and no account.

**What SOLASI can do**

- Controls one or two batteries together for zero feed-in, with solar power going to the house first
- Eco mode that protects the battery and learns the nightly base load
- Surplus for heating element, wall box (continuously variable) and switches
- Anker SOLIX, Marstek and other storage types, plus a custom script for everything else
- Live overview with energy flow, dashboard card, statistics and "what if" replay (*Was wäre wenn*)
- Fixed entities via MQTT: sensors, energy counters for the Energy dashboard and switches (control, *Testmodus*, *Not-Aus*)
- Safety: *Testmodus*, *Not-Aus*, fallback to the manufacturer's mode, watchdog and notifications

**Getting started**

1. **Start** the add-on and turn on **Show in sidebar**.
2. Open **SOLASI** in the sidebar. The *Willkommensseite* (welcome page) guides you through the setup.
3. Begin with **Testmodus** switched on: SOLASI then calculates everything but sends nothing. In the *Protokoll* (log) you can see what would happen.
4. Only when everything looks plausible, switch *Testmodus* off.

You can find the detailed guide in the **Documentation** tab.

**Important:** SOLASI controls real hardware. Use at your own risk, without warranty. Observe the feed-in limits of your system and your grid operator's requirements.
SOLASI is an independent project and is not affiliated with SolarAssistant, Anker or other manufacturers.
