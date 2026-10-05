# SOLASI

Nulleinspeisung für **ein oder zwei Anker SOLIX 4 E5000 Pro** (offizielle lokale Integration „Anker Solix Official“)
mit Live-Übersicht, Eco-Modus, Abregelung bei vollem Speicher und Überschusssteuerung für Verbraucher
(Ein/Aus und stufenlos für Wallbox und Heizstab). Alle Einstellungen nimmst du in der Oberfläche von SOLASI vor,
es ist keine YAML-Datei und kein Blueprint nötig.

*SOLASI = SOLar-Anlagen-Speicher-Interface. Unabhängiges Projekt, nicht verbunden mit SolarAssistant (solar-assistant.io) oder Anker.*

## Inbetriebnahme

1. **Alte Blueprint-Automation ausschalten.** Zwei Regler gleichzeitig würden gegeneinander arbeiten.
2. Add-on starten und in der Seitenleiste **SOLASI** öffnen.
3. Unter **Einstellungen → Anlage** Netzsensor (Bitshake), je Speicher den **Speichertyp** und die dazu passenden Entitäten (bei Anker: Leistung (number), Leistungsfluss (select),
   Betriebsmodus (select) und SOC wählen. Die echten Lade-/Entladesensoren sind optional, aber für Failsafe
   und Hausverbrauchsberechnung empfehlenswert. **Speichern** nicht vergessen.
4. Oben **Regelung aktiv** einschalten und den **Testmodus** angeschaltet lassen. SOLASI berechnet dann alles,
   sendet aber nichts. Unter **System → Protokoll** steht, was gesendet würde („Test: Speicher A: 0 W → 280 W …“).
5. Stimmen Richtung und Werte, den **Testmodus ausschalten**. Ab jetzt steuert SOLASI die Geräte.

Die Schalter oben in der Kopfzeile wirken sofort und werden automatisch gespeichert.

## Dashboard-Karte

SOLASI installiert beim Start automatisch die Karte `solasi-card` und versucht, sie als Dashboard-Ressource einzutragen.
Unter **System → Dashboard-Karte** siehst du, was geklappt hat, und findest bei Bedarf die manuelle Anleitung.

Karte hinzufügen: Dashboard bearbeiten → *Karte hinzufügen* → **SOLASI** wählen, oder „Manuell“:

```yaml
type: custom:solasi-card
entity: sensor.solasi        # optional
title: SOLASI                # optional, "" blendet den Titel aus
show_headline: true           # Klartext-Überschrift
show_batteries: true          # Ladestand je Speicher
show_surplus: true            # Überschuss und Verbraucher
show_tags: true               # Eco, Zähler, Sollwert
```

SOLASI legt dafür diese Entitäten in Home Assistant an (auch für eigene Karten, Verläufe und Automationen nutzbar):
`sensor.solasi` (Status, alle Werte als Attribute), `sensor.solasi_pv_power`, `sensor.solasi_house_power`,
`sensor.solasi_battery_power` (+ entlädt, − lädt), `sensor.solasi_target_power`, `sensor.solasi_surplus_power`.
Es sind virtuelle Entitäten ohne Eintrag in der Entitäten-Verwaltung. Sie verschwinden bei einem Neustart von
Home Assistant und werden von SOLASI sofort wieder angelegt.

Falls die automatische Installation nicht klappt: `solasi-card.js` nach `/config/www/solasi/` kopieren und unter
*Einstellungen → Dashboards → ⋮ → Ressourcen* als JavaScript-Modul mit der URL `/local/solasi/solasi-card.js` eintragen.
Wurde der Ordner `www` neu angelegt, muss Home Assistant einmal neu gestartet werden.

## Kill-Switch und Sicherheit

Ein Speicher im externen Modus (z. B. „third_party_control“) arbeitet mit dem **letzten Sollwert** weiter, auch wenn niemand mehr
regelt. SOLASI sichert das in mehreren Schichten ab:

1. **Not-Aus-Knopf** oben (⛔): Stoppt SOLASI sofort. Alle Speicher gehen auf 0 W und in den **Rückfall-Modus**, den du je Speicher
   unter *Einstellungen → Anlage → „Beim Stoppen: Modus setzen auf“* wählst (bei Anker z. B. „self_consumption“, in der Anker-App
   „Eigenverbrauch“; die Vorschläge stammen aus dem Betriebsmodus des Speichers). Danach prüft SOLASI, ob der Modus wirklich
   gesetzt wurde, und meldet es, wenn nicht. Der Knopf wird zu **▶ Fortsetzen**. Der Stopp bleibt auch nach einem Neustart bestehen.
2. **Not-Aus-Schalter in Home Assistant** (optional): Unter *Sicherheit & Meldungen* kannst du einen Schalter oder input_boolean
   wählen. Ist er „an“, stoppt SOLASI, wird er „aus“, läuft es weiter. Damit lässt sich SOLASI aus Automationen,
   Dashboards oder per Taster stoppen.
3. **Automatisch stoppen**: bei Zählerausfall länger als eingestellt (Standard 5 Minuten, bis dahin stehen die Speicher auf 0 W)
   und wenn Steuerbefehle wiederholt fehlschlagen. Auf Wunsch setzt SOLASI danach nach 5 Minuten ohne Störung selbst fort,
   sonst bleibt es gestoppt, bis du „Fortsetzen“ drückst.
4. **Beim Beenden** (Add-on stoppen, neu starten, aktualisieren) gibt SOLASI die Speicher frei. Ebenso, wenn du die
   Live-Steuerung ausschaltest oder in den Testmodus wechselst.
5. **Wächter für den Absturz** (automatisch): Fällt SOLASI hart aus, kann es selbst nichts mehr zurückstellen. Deshalb sendet
   SOLASI alle 30 Sekunden ein Lebenszeichen (`sensor.solasi_heartbeat`) und legt in Home Assistant eine eigene Automation
   **„SOLASI Wächter“** an. Sie läuft unabhängig von SOLASI: Bleibt das Lebenszeichen länger aus (Standard 3 Minuten) oder meldet
   sich SOLASI nach einem Neustart von Home Assistant nicht, stellt sie die Speicher auf den Rückfall-Modus zurück, schaltet
   Fernsteuerungs-Schalter aus und schickt eine Meldung. SOLASI hält die Automation bei jeder Änderung der Einstellungen
   aktuell und entfernt sie, wenn du den Wächter ausschaltest. Beendest du SOLASI selbst (Add-on stoppen oder aktualisieren),
   meldet es „stopped“ und der Wächter greift nicht ein, weil die Speicher dann schon freigegeben sind.
   Änderungen, die du von Hand an dieser Automation machst, werden beim nächsten Abgleich überschrieben. Darf SOLASI keine
   Automationen anlegen, zeigt *Sicherheit & Meldungen* den Zustand „manuell“ und den fertigen Text zum Einfügen.

Bei den anderen Speichertypen bedeutet „Freigabe“: Modus-Typ auf Stop und Leistungen auf 0, Fernsteuerung aus, Rückfall-Modus
setzen. Beim Ausgangslimit wird ein Rückfall-Limit gesetzt, wenn eines eingetragen ist. Beim Skript-Typ wird das Skript mit
`mode: release` und `power_w: 0` aufgerufen.

Grenzen: Ist Home Assistant selbst nicht erreichbar (Absturz, Neustart), kann SOLASI keine Befehle senden. Auch ein
hart abgebrochener Docker-Container kann nichts mehr zurückstellen, dafür gibt es den Wächter.

## Sicherung der Einstellungen

Unter *Sicherheit & Meldungen → Sicherung der Einstellungen* kannst du alle Einstellungen als Datei herunterladen und wieder einspielen,
zum Beispiel als Sicherung oder für eine neue Installation.

## Bedienung

Die Oberfläche hat vier Bereiche: **Übersicht**, **Einstellungen** (Anlage, Regelung, Überschuss, Sicherheit & Meldungen),
**Auswertung** (Statistik, Replay) und **System** (Selbsttest, Protokoll, Dashboard-Karte). Gruppen lassen sich ein- und
ausklappen. Standardmäßig siehst du nur das Wesentliche. Mit dem Schalter **Experte** oben erscheinen zusätzliche
Feineinstellungen (Mindestabstand, Schwellen, Offsets, Hysterese, Verzögerungen, Namen der Optionen und mehr).

## Speichertypen

SOLASI ist nicht auf Anker festgelegt. Je Speicher wählst du unter *Einstellungen → Anlage* den **Speichertyp**:

| Typ | So wird gesteuert | Passt z. B. zu |
|---|---|---|
| Anker SOLIX (Betrag + Richtung) | Zahl für die Leistung + Auswahl für die Richtung, Modus-Wächter | Anker Solarbank 4 E5000 Pro, Max AC |
| Eine Zahl mit Vorzeichen | Eine Zahl: positiv = Entladen, negativ = Laden (umstellbar), optional Arbeitsmodus | Marstek im Passiv-Modus |
| Modus + Leistungen | Auswahl Stop/Laden/Entladen + Zahl für Entlade- und Ladeleistung, optional Fernsteuerung und Arbeitsmodus | Marstek über Modbus |
| Ausgangslimit (nur Entladen) | Eine Zahl begrenzt die Abgabe, kein Netzladen | Wechselrichter-Limit (z. B. OpenDTU) |
| Eigenes Skript | Ruft ein Skript mit `power_w`, `mode` und `unit` auf | alles andere (Victron, Huawei, Sungrow …) |

Die Typen lassen sich mischen, z. B. ein Anker und ein Marstek. Die Regelung verteilt den Sollwert wie bisher.
Speichertypen ohne Netzladen (Ausgangslimit, Modus ohne Ladezahl) werden bei Überschuss nie zum Laden eingeplant.
Die Auswahl der Entitäten, Optionsnamen und Leistungssensoren (mit Vorzeichen) hängt vom Typ ab. Der Selbsttest prüft sie typgerecht.

**Skript-Typ:** Das Skript bekommt beim Aufruf diese Felder:

```yaml
script:
  mein_speicher_setzen:
    fields:
      power_w: { description: "Sollwert in W: positiv = Entladen, negativ = Laden" }
      mode:    { description: "discharge, charge oder idle" }
      unit:    { description: "Name des Speichers" }
    sequence:
      - action: number.set_value
        target: { entity_id: number.mein_speicher_leistung }
        data: { value: "{{ power_w }}" }
```

SOLASI merkt sich beim Skript-Typ den zuletzt gesendeten Sollwert, weil der aktuelle Wert nicht ausgelesen werden kann.
Die beschriebenen Typen sind anhand der Dokumentation der jeweiligen Integrationen umgesetzt und im Simulator getestet,
nicht an echter Hardware. Beim ersten Einsatz bitte zuerst im Testmodus beobachten.

## Sensoren, Messart und PV-Durchleitung

**Sensoren wählen:** Unter *Einstellungen → Anlage* zeigt jeder Speicher die Sensoren desselben Geräts mit aktuellem Wert. Vergleiche sie mit der
Hersteller-App, um Solar, Laden und Entladen zu finden. Die Felder schlagen diese Sensoren zuerst vor.

**Messart der Leistungssensoren:**

| Messart | Bedeutung | Abgabe ins Haus |
|---|---|---|
| Batterie (DC) | Lade-/Entladeleistung der Batterie (typisch bei Anker) | Solar + Batterie |
| Haus-Anschluss (AC) | Leistung, die der Speicher an das Haus abgibt bzw. aus dem Netz zieht | direkt gemessen |

„Automatisch“ nimmt bei Anker mit PV-Sensor die Batterieseite, sonst AC. Beispiel Anker: 540 W Solar, Batterie lädt 140 W → 400 W gehen ins Haus.
**Selbsttest → Energiebilanz** zeigt die berechneten Werte zum Vergleich mit der Hersteller-App. Weichen sie ab, ist meist die Messart oder ein Sensor falsch.

**Unbekannt ist nicht 0:** Ist ein Sensor nicht verfügbar, zeigt SOLASI „–“ und rechnet davon abhängige Werte nicht mit 0 W.

**PV-Durchleitung:** Liegt der Ladestand unter dem Minimum, darf ein Speicher trotzdem so viel abgeben, wie seine Module gerade liefern (minus 10 W).
Die Batterie wird dabei nicht entladen. Der Eco-Modus begrenzt nur den Anteil aus der Batterie, die PV kommt zusätzlich direkt ins Haus.
Das setzt voraus, dass der Speicher im externen Modus die PV zuerst nutzt. Bitte im Testmodus beobachten, dann live mit dem Not-Aus in Reichweite prüfen.

## Selbsttest und Systemprüfung

**System → Selbsttest** enthält zwei Dinge:

- **Systemprüfung:** Prüft per Knopfdruck alle gewählten Entitäten (existieren sie, liefern sie Zahlen, stimmt die Einheit,
  gibt es die Optionen `third_party_control`, `charge` und `discharge`) und gibt konkrete Hinweise zur Behebung.
- **Abregelungs-Wächter:** Läuft dauerhaft mit. Sind alle Speicher voll und scheint die Sonne, prüft SOLASI, ob trotzdem
  eingespeist wird. Nach drei Minuten Einspeisung gilt die Abregelung als *nicht wirksam*. Dann dürfen Verbraucher der
  Überschusssteuerung unabhängig vom Ladestand laufen, und du bekommst eine Meldung. Bleibt der Zähler dagegen ausgeglichen,
  gilt die Abregelung als *bestätigt*.

## Benachrichtigungen

Unter *Einstellungen → Sicherheit & Meldungen* wählst du ein Ziel (z. B. `notify.mobile_app_dein_handy` oder `persistent_notification`)
und die Ereignisse: Zähler ohne Meldung, Speicher nicht erreichbar, Speicher leer, Einspeisung trotz vollem Speicher,
fehlschlagende Steuerbefehle. Gemeldet wird erst nach einer einstellbaren Dauer, dieselbe Meldung kommt frühestens nach der
Sperrzeit wieder, und bei Entwarnung folgt eine Nachricht. Mit „Testnachricht senden“ prüfst du das Ziel.

## Grundlast lernen

SOLASI misst nachts (PV unter 20 W, sonst Sonnenstand, sonst 1 bis 5 Uhr) den Hausverbrauch und bildet je Nacht den
Median. Der Median der letzten sieben Nächte ist die gelernte Grundlast. Mit „Eco-Leistung aus gelernter Grundlast“
nutzt der Eco-Modus diesen Wert plus Zuschlag, begrenzt auf ein Minimum und Maximum. Dafür werden die echten Lade-/
Entladesensoren oder ein Hausverbrauchs-Sensor gebraucht. Der gelernte Wert liegt auch als `sensor.solasi_base_load` vor.

## Statistik

SOLASI integriert Leistung zu Energie und zeigt je Tag Verbrauch, PV, Netzbezug, Einspeisung und Speicherdurchsatz,
dazu Autarkie, Eigenverbrauch und Beträge nach deinen Preisen. Die Werte sind Näherungen aus dem Regeltakt.

## Replay

**Auswertung → Replay** spielt echte Verlaufsdaten (bis 72 Stunden) aus dem Recorder durch die Regelung. Du kannst einzelne
Einstellungen ändern und siehst Netzbezug, Einspeisung, Ladestand, Eco-Zeit und Schaltvorgänge im Vergleich zu den gemessenen
Werten und zu den aktuellen Einstellungen. Voraussetzung sind Netzsensor sowie je Speicher Ladestand, echte Lade- und
Entladeleistung und PV-Leistung. **Das Modell ist eine Näherung:** Lastgang und PV kommen aus der Historie, der Speicher wird
vereinfacht nachgebildet. Der „Modell-Check“ zeigt, wie weit die Simulation mit den aktuellen Einstellungen vom Gemessenen abweicht.
Mit der Annahme „Firmware drosselt PV bei vollem Speicher“ kannst du beide Möglichkeiten durchspielen.

## Funktionen

| Funktion | Beschreibung |
|---|---|
| Gemeinsamer Regler | Berechnet den Gesamtsollwert und verteilt ihn gleichmäßig, nach Ladestand oder nacheinander auf beide Geräte |
| Eco-Modus | Begrenzt die Gesamtentladung ab einem mittleren SOC auf die Grundlast |
| Schwellen & Hysterese | Ein-/Ausschaltschwellen, SOC-Hysterese, getrennte Offsets für Laden und Entladen |
| AC-Laden | Fremd-Überschuss (z. B. andere PV-Anlage) darf den Akku laden |
| Strenge Nulleinspeisung | Voller Speicher wird auf Entladen 0 W bzw. Hausbedarf gestellt, damit die PV gedrosselt wird |
| Failsafe | Fällt der Zähler aus, werden die Geräte auf 0 W gesetzt; Real-Power-Check |
| Überschuss | Bis zu 3 Verbraucher mit eigenen Schwellen, Verzögerungen, Mindestlaufzeiten, SOC-Bedingung, Zusatzbedingung |
| Stufenlose Regelung | Wallbox (Ladestrom) oder Heizstab (Leistung/Prozent) folgen dem Überschuss |
| Entladesperre | Pro Verbraucher: Der Speicher speist ihn nicht aus dem Akku |

Jede Zusatzfunktion lässt sich einzeln ausschalten.

## Hinweise

- **Zähler:** Am besten der rohe Bitshake-Wert oder ein Mittelwert über wenige Sekunden. Ein Median über Minuten macht die Regelung träge.
- **Mindestabstand:** Viele Speicher melden Werte nur etwa alle 5 Sekunden. Unter 4 Sekunden schwingt die Regelung meist.
- **Gesamtlimit:** Voreingestellt sind konservative 800 W. Für größere angemeldete Anlagen erhöhen.
- **Abregelung bei vollem Speicher:** Ob die Firmware die PV dann wirklich drosselt, lässt sich nur live prüfen
  (sonniger Tag, voller Speicher, wenig Verbrauch, Zähler beobachten).
- **Überschuss für Wallbox/Heizstab:** Als Quelle „PV minus Hausverbrauch“ wählen und die PV-Sensoren je Gerät eintragen.
- **Zugriff:** Die Oberfläche ist nur über Home Assistant (Ingress) erreichbar.
- Einstellungen liegen in `/data/settings.json` und sind Teil der Home-Assistant-Backups.
