# SOLASI – Anleitung

SOLASI regelt deinen Batteriespeicher so, dass dein Haus möglichst viel Solarstrom selbst verbraucht: kaum Einspeisung ins Netz, kaum Bezug aus dem Netz.
Alle Einstellungen nimmst du in der Oberfläche von SOLASI vor (Seitenleiste in Home Assistant), du brauchst keine Konfigurationsdatei.

> **Wichtig:** SOLASI steuert echte Hardware. Fang immer im **Testmodus** an (Schritt 5 der Einrichtung) und lerne den **Not-Aus** kennen (Kapitel „Sicherheit“).

## Inhalt

1. [Voraussetzungen](#voraussetzungen)
2. [Einrichtung Schritt für Schritt](#einrichtung-schritt-für-schritt)
3. [Die Oberfläche](#die-oberfläche)
4. [Speichertypen](#speichertypen)
5. [Regelung und Einstellungen](#regelung-und-einstellungen)
6. [Überschuss für Verbraucher, Wallbox und Heizstab](#überschuss-für-verbraucher-wallbox-und-heizstab)
7. [Sicherheit und Not-Aus](#sicherheit-und-not-aus)
8. [Benachrichtigungen](#benachrichtigungen)
9. [Auswertung: Statistik und Replay](#auswertung-statistik-und-replay)
10. [Selbsttest und Energiebilanz](#selbsttest-und-energiebilanz)
11. [Dashboard-Karte](#dashboard-karte)
12. [Feste Entitäten und Energie-Dashboard (MQTT)](#feste-entitäten-und-energie-dashboard-mqtt)
13. [Sicherung der Einstellungen](#sicherung-der-einstellungen)
14. [Häufige Fragen und Fehlersuche](#häufige-fragen-und-fehlersuche)
15. [Datenschutz und Haftung](#datenschutz-und-haftung)

## Voraussetzungen

- Home Assistant mit Add-on-Store (Home Assistant OS oder Supervised).
- Dein Speicher ist in Home Assistant eingebunden. Bei der **Anker SOLIX Solarbank 4 E5000 Pro** über die offizielle Integration *Anker Solix Official*.
- Ein **Sensor für die Netzleistung in Watt** (positiv = Bezug, negativ = Einspeisung), zum Beispiel ein Lesekopf am Stromzähler oder ein Shelly EM.
  Am besten der rohe oder kurz geglättete Wert, nicht ein Durchschnitt über Minuten, sonst reagiert die Regelung träge.
- Empfohlen: Sensoren für die **Solarleistung** und für **Laden und Entladen** deines Speichers.

Nutzt du bisher eine Automation oder einen Blueprint zur Nulleinspeisung, **schalte ihn aus**, bevor SOLASI live steuert. Zwei Regler gleichzeitig arbeiten gegeneinander.

## Einrichtung Schritt für Schritt

1. **SOLASI öffnen.** Die Willkommensseite führt dich zu *Einrichtung*.
2. **Zähler wählen.** Trage den Sensor der Netzleistung ein. Zeigt dein Zähler Einspeisung als positiven Wert, schalte „Vorzeichen umkehren“ ein.
3. **Speicher einrichten.** Wähle den **Speichertyp** und die passenden Entitäten. Die Felder schlagen sie vor, die Sensoren desselben Geräts stehen mit aktuellem Wert vorn.
   Bei der Anker SOLIX sind das:
   - **Leistung (number):** die Entität „Leistungssteuerung“
   - **Leistungsfluss / Richtung (select):** Laden oder Entladen
   - **Betriebsmodus (select):** der Modus des Speichers. SOLASI schaltet ihn auf externe Steuerung (`third_party_control`)
   - **Ladestand (SOC)** sowie, empfohlen, **PV-Leistung**, **Entlade-** und **Ladeleistung**
   - **Beim Stoppen: Modus setzen auf:** der Modus, den der Speicher bekommt, wenn SOLASI stoppt, bei Anker meist „self_consumption“ (in der Anker-App „Eigenverbrauch“)
4. **Messart prüfen.** Messen deine Lade- und Entladesensoren die Batterie oder die Abgabe ans Haus? Bei Anker mit PV-Sensor stimmt „Automatisch“. Details im Kapitel [Selbsttest und Energiebilanz](#selbsttest-und-energiebilanz).
5. **Im Testmodus starten.** Schalte oben **Regelung** ein und lass **Testmodus** an. SOLASI rechnet dann alles durch, sendet aber nichts. Unter *System → Protokoll* steht, was passieren würde
   (zum Beispiel „Test: Speicher A: 0 W → 280 W“).
6. **Selbsttest ausführen** (*System → Selbsttest*). Er meldet fehlende oder falsche Entitäten mit einem Lösungsvorschlag.
7. **Live schalten.** Wenn Richtung und Werte plausibel sind, den **Testmodus ausschalten**. Ab jetzt steuert SOLASI den Speicher und stellt ihn bei Bedarf auf externe Steuerung.

Die Schalter oben wirken sofort und werden automatisch gespeichert. Änderungen in den Formularen gelten erst nach **Speichern**.

## Die Oberfläche

Links steht die Seitenleiste, am Handy eine Leiste unten (der Rest steckt im Menü **Mehr**).

| Bereich | Inhalt |
|---|---|
| **Betrieb** | *Übersicht* (Kennzahlen, Zähler, Energiefluss, Speicher, Überschuss, Protokoll), *Speicher*, *Überschuss*, *Zähler* |
| **Auswertung** | *Statistik* und *Replay* |
| **System** | *Selbsttest*, *Protokoll*, *Dashboard-Karte*, *Entitäten (MQTT)* |
| **Einrichtung** | Zähler und Speicher einrichten, auch als Assistent beim ersten Start |
| **Einstellungen** | *Regelung*, *Sicherheit & Meldungen*, *Darstellung* |

Die Kopfleiste zeigt Verbindung und Modus (**Live**, **Testmodus**, **Beobachten** oder **Gestoppt**) und enthält die Schalter **Regelung** und **Testmodus** sowie den **Not-Aus**, der vor dem Auslösen nachfragt.
Ein Hinweisband erscheint, wenn etwas Aufmerksamkeit braucht. Unter *Einstellungen → Darstellung* wählst du Startseite und Dichte; beides gilt nur für das jeweilige Gerät.

**Der Verlauf** unter dem Energiefluss zeigt die letzten 24 Stunden: Solar als Fläche, Haus als Linie, der Punkt ist der aktuelle Wert. Die Dashboard-Karte zeigt dieselbe Grafik.

**Den Energiefluss lesen:** Die Ladeleistung der Batterie kommt zuerst aus der Solarleistung (Linie *Solar → Speicher*), der Rest geht ins Haus. Reicht die Solarleistung nicht, kommt der Rest der Ladung aus dem Netz
und läuft über das Haus in den Speicher. Beim Entladen gibt der Speicher über die Linie *Speicher → Haus* ab. Die Verteilung ist aus den Messwerten abgeleitet, die Anlage meldet sie nicht selbst.
Unbekannte Werte zeigt SOLASI als „–“, nie als 0 W.

## Speichertypen

SOLASI ist nicht auf einen Hersteller festgelegt. Je Speicher wählst du unter *Einrichtung* den **Speichertyp**. Typen lassen sich mischen.

| Typ | So wird gesteuert | Passt z. B. zu |
|---|---|---|
| Anker SOLIX (Betrag + Richtung) | Zahl für die Leistung, Auswahl für die Richtung | Anker Solarbank 4 E5000 Pro |
| Eine Zahl mit Vorzeichen | Eine Zahl: positiv = Entladen, negativ = Laden (umstellbar), optional Arbeitsmodus | Marstek im Passiv-Modus |
| Modus + Leistungen | Auswahl Stop / Laden / Entladen plus Zahlen für Entlade- und Ladeleistung, optional Fernsteuerung und Arbeitsmodus | Marstek über Modbus |
| Ausgangslimit (nur Entladen) | Eine Zahl begrenzt die Abgabe, kein Laden aus dem Netz | Wechselrichter-Limit (z. B. über OpenDTU) |
| Eigenes Skript | Ruft ein Home-Assistant-Skript auf | alles andere (Victron, Huawei, Sungrow …) |

Speichertypen ohne Netzladen (Ausgangslimit, Modus ohne Ladezahl) werden bei Überschuss nie zum Laden eingeplant.

> **Stand:** Die Anker SOLIX ist im Praxiseinsatz entwickelt und getestet. Die anderen Typen sind nach den Beschreibungen der jeweiligen Integrationen umgesetzt und bisher nur in Simulationen geprüft.
> Beobachte sie bitte zuerst im Testmodus und gib gern Rückmeldung.

**Eigenes Skript:** SOLASI ruft das Skript mit diesen Feldern auf. Beim Zurückgeben des Speichers (Not-Aus) ist `mode` gleich `release` und `power_w` gleich 0.

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

SOLASI merkt sich beim Skript den zuletzt gesendeten Sollwert, weil er sich nicht auslesen lässt.

## Regelung und Einstellungen

### Wie SOLASI regelt
SOLASI liest den Zähler und rechnet daraus den Sollwert für den Speicher. Es lässt bewusst ein paar Watt Netzbezug übrig (voreingestellt 10 W), damit kein Akkustrom ins Netz fließt.
Bei zwei Speichern wird der Sollwert aufgeteilt: gleichmäßig, nach Ladestand oder nacheinander.

### Funktionen (*Einstellungen → Regelung*)
Jede Funktion lässt sich einzeln ein- und ausschalten.

| Funktion | Was sie tut |
|---|---|
| **Eco-Modus** | Begrenzt die Abgabe aus der Batterie bei niedrigem Ladestand auf die Grundlast, damit der Akku bis zum Morgen reicht. Solarleistung kommt zusätzlich direkt ins Haus |
| **Schwellen verwenden** | Reagiert erst ab einer Mindestabweichung (voreingestellt 120 W ein, 80 W aus). Verhindert unruhiges Schalten |
| **Laden aus Fremd-Überschuss erlauben** | Der Akku darf auch mit Überschuss anderer Erzeuger am Zähler geladen werden |
| **Strenge Nulleinspeisung bei vollem Speicher** | Ein voller Speicher wird auf „Entladen“ gestellt, damit die Solarleistung gedrosselt wird statt ins Netz zu gehen. Ob der Speicher das umsetzt, hängt von seiner Firmware ab. Der Selbsttest beobachtet es |
| **Externe Steuerung automatisch einschalten** | Sobald SOLASI live steuert, stellt es den Betriebsmodus des Speichers auf externe Steuerung (bei Anker `third_party_control`): beim Start, nach „Fortsetzen“ und wenn der Modus von außen verstellt wird. Zum Zurückgeben dient der Not-Aus |
| **PV direkt ins Haus geben, auch bei leerem Speicher** | Liegt der Ladestand unter dem Minimum, darf der Speicher trotzdem so viel abgeben, wie seine Module gerade liefern. Die Batterie wird dabei nicht entladen. Braucht den PV-Sensor |
| **Failsafe** | Fällt der Zähler aus, gehen die Speicher auf 0 W. Fließt noch Leistung, obwohl 0 W gewollt sind, wird 0 W erneut gesendet |

### Grenzen und Akku
- **Gesamtlimit Entladung / Laden:** Voreingestellt sind vorsichtige 800 W für die Abgabe. Passe es an deine Anlage und die Vorgaben deines Netzbetreibers an.
- **Nicht entladen unter / Nicht laden über:** Ladestandsgrenzen (voreingestellt 15 % und 99 %). Eine Hysterese verhindert Hin- und Herschalten an der Grenze.
- **Eco-Modus ab mittlerem Ladestand** (voreingestellt 35 %) und **Eco-Entladeleistung** (150 W) legen fest, wann und wie stark Eco bremst.
- **Grundlast lernen:** Mit „Eco-Leistung aus gelernter Grundlast“ misst SOLASI nachts den Verbrauch deines Hauses und passt die Eco-Leistung selbst an (Median der letzten sieben Nächte plus Zuschlag).
  Dafür braucht es Sensoren für Laden und Entladen oder einen Hausverbrauchs-Sensor. Der gelernte Wert steht in den Einstellungen und als `sensor.solasi_base_load`.

### Sensoren und Messart
Unter *Einrichtung* zeigt jeder Speicher die **Sensoren desselben Geräts mit aktuellem Wert**. Vergleiche sie mit der Hersteller-App, um Solar, Laden und Entladen zu finden.

**Messart der Leistungssensoren:**

| Messart | Bedeutung | Abgabe ins Haus |
|---|---|---|
| Batterie (DC) | Lade- und Entladeleistung der Batterie (typisch bei Anker) | Solar + Batterie |
| Haus-Anschluss (AC) | Leistung, die der Speicher ans Haus abgibt bzw. aus dem Netz zieht | direkt gemessen |

„Automatisch“ nimmt bei Anker mit PV-Sensor die Batterieseite, sonst AC. Beispiel Anker: 540 W Solar, Batterie lädt 140 W → 400 W gehen ins Haus.

## Überschuss für Verbraucher, Wallbox und Heizstab

Unter *Betrieb → Überschuss* richtest du bis zu **drei Verbraucher** ein, die laufen, wenn mehr Solarstrom da ist, als das Haus braucht. Dort schaltest du die Funktion auch ein.
Der **Überschuss-Test** protokolliert nur, was geschaltet würde.

- **Quelle des Überschusses:** *PV minus Hausverbrauch* (empfohlen, braucht PV-Sensoren), *Einspeisung ins Netz* oder ein *eigener Sensor*.
- **Ein- und Ausschalten:** Jeder Verbraucher hat eine Einschaltschwelle (Überschuss in Watt), eine Ausschaltschwelle (Defizit), Verzögerungen, Mindestlaufzeit und Mindestpause. Die Verbraucher haben eine Reihenfolge,
  der erste hat Priorität. Niedrigere Prioritäten bekommen sinnvollerweise kleinere Ausschaltschwellen, damit sie zuerst ausgehen.
- **Ladestand-Bedingung:** Verbraucher laufen erst, wenn der mittlere Ladestand einen Wert erreicht hat. So haben die Speicher Vorrang.
- **Stufenlos (Wallbox, Heizstab):** Trage eine Entität (number) für den Ladestrom bzw. die Leistung ein, dazu die **Watt pro Einheit** (Wallbox einphasig 230 W je Ampere, dreiphasig 690 W je Ampere, Heizstab in Watt: 1),
  Mindest- und Maximalleistung. SOLASI führt den Wert dem Überschuss nach und rundet auf die Schrittweite der Entität ab, damit sie den Überschuss nie übersteigt.
- **Nicht aus dem Akku versorgen:** Der Speicher speist diesen Verbraucher dann nicht, er läuft aus Solarstrom oder Netz.

## Sicherheit und Not-Aus

Ein Speicher im externen Modus arbeitet mit dem **letzten Sollwert** weiter, auch wenn niemand mehr regelt. SOLASI sichert das in mehreren Schichten ab:

1. **Not-Aus-Knopf (⛔) oben.** Er stoppt SOLASI sofort. Alle Speicher gehen auf 0 W und in den **Rückfall-Modus** (zum Beispiel Eigenverbrauch). SOLASI prüft danach, ob der Modus gesetzt wurde, und meldet es, wenn nicht.
   Der Knopf wird zu **▶ Fortsetzen**. Der Stopp bleibt auch nach einem Neustart bestehen.
2. **Not-Aus-Schalter in Home Assistant** (optional, *Sicherheit & Meldungen*): Ist ein gewählter Schalter „an“, stoppt SOLASI, wird er „aus“, läuft es weiter. So lässt sich SOLASI auch aus Automationen oder per Taster stoppen.
3. **Automatisch stoppen** bei Zählerausfall (voreingestellt nach 5 Minuten, bis dahin stehen die Speicher auf 0 W) und wenn Steuerbefehle wiederholt fehlschlagen. Auf Wunsch macht SOLASI danach nach 5 ruhigen Minuten selbst weiter,
   sonst bleibt es gestoppt, bis du „Fortsetzen“ drückst.
4. **Freigabe beim Beenden:** Stoppst, startest oder aktualisierst du das Add-on, gibt SOLASI die Speicher frei. Ebenso, wenn du die Live-Steuerung ausschaltest oder in den Testmodus wechselst.
5. **Wächter für den Absturz.** Fällt SOLASI plötzlich komplett aus, kann es selbst nichts mehr zurückstellen. Deshalb sendet es alle 30 Sekunden ein Lebenszeichen und legt in Home Assistant die Automation **„SOLASI Wächter“** an.
   Sie läuft unabhängig: Bleibt das Lebenszeichen länger aus (voreingestellt 3 Minuten) oder meldet sich SOLASI nach einem Neustart von Home Assistant nicht, stellt sie die Speicher auf den Rückfall-Modus und schickt eine Meldung.
   Beendest du SOLASI selbst, greift der Wächter nicht ein, weil die Speicher dann schon frei sind. SOLASI hält die Automation aktuell. Änderungen, die du von Hand an ihr vornimmst, werden überschrieben.
   Darf SOLASI keine Automation anlegen, zeigt *Sicherheit & Meldungen* den fertigen Text zum Einfügen.

**Rückfall-Modus festlegen:** Trage ihn bei jedem Speicher unter *Einrichtung* im Feld „Beim Stoppen: Modus setzen auf“ ein. Ohne ihn bleibt der Speicher im externen Modus mit 0 W.

**Möchtest du kurz in der Hersteller-App umstellen?** Nimm vorher den Not-Aus, sonst stellt SOLASI den Modus nach spätestens 30 Sekunden zurück.

**Grenzen:** Ist Home Assistant selbst nicht erreichbar, kann SOLASI keine Befehle senden. Beachte die gesetzlichen Einspeisegrenzen deiner Anlage.

## Benachrichtigungen

Unter *Einstellungen → Sicherheit & Meldungen* wählst du ein Ziel, zum Beispiel `notify.mobile_app_dein_handy` für eine Mitteilung aufs Handy oder `persistent_notification` für die Glocke in Home Assistant.
Gemeldet wird bei: Zähler ohne Meldung, Speicher nicht erreichbar, Speicher leer, Einspeisung trotz vollem Speicher, fehlschlagende Steuerbefehle und wenn SOLASI gestoppt wurde.
Eine Meldung kommt erst, wenn die Störung eine einstellbare Zeit dauert, dieselbe Meldung wiederholt sich frühestens nach einer Sperrzeit, und bei Entwarnung folgt eine Nachricht. Mit **Testnachricht senden** prüfst du das Ziel.

## Auswertung: Statistik und Replay

**Statistik:** Pro Tag siehst du Verbrauch, Solarertrag, Netzbezug, Einspeisung und Speicherdurchsatz, dazu **Autarkie**, **Eigenverbrauch** und Beträge nach deinen Preisen (*Sicherheit & Meldungen → Preise*).
Die Werte sind Näherungen. Für den Hausverbrauch braucht SOLASI Sensoren für Laden und Entladen (oder einen Hausverbrauchs-Sensor).

**Replay:** *Auswertung → Replay* spielt echte Verlaufsdaten der letzten Stunden (bis 72) durch die Regelung. Du kannst einzelne Einstellungen ändern und siehst Netzbezug, Einspeisung, Ladestand, Eco-Zeit und
Schaltvorgänge im Vergleich zu den gemessenen Werten und zu deinen aktuellen Einstellungen. Voraussetzung sind Netzsensor sowie je Speicher Ladestand, Lade- und Entladeleistung und PV-Leistung, außerdem ein aktiver Recorder.
Das Replay ist eine **Näherung**. Der „Modell-Check“ zeigt, wie weit die Simulation mit deinen Einstellungen vom Gemessenen abweicht. Mit der Annahme „Firmware drosselt PV bei vollem Speicher“ spielst du beide Möglichkeiten durch.

## Selbsttest und Energiebilanz

**System → Selbsttest** zeigt:

- **Systemprüfung:** Sie prüft alle gewählten Entitäten (gibt es sie, liefern sie Zahlen, stimmt die Einheit, gibt es die nötigen Optionen) und nennt zu jedem Problem eine Lösung. Außerdem prüft sie Rückfall-Modus, Not-Aus-Schalter und Benachrichtigungen.
- **Energiebilanz:** Solar, Batterie, Abgabe ins Haus, Netz und Haus, berechnet aus deinen Sensoren. **Vergleiche diese Werte mit der Hersteller-App.** Weichen sie ab, ist meist die Sensorauswahl oder die Messart falsch.
  Eine Warnung erscheint auch, wenn Ladesensoren eher nach Batterie- als nach Netzleistung aussehen.
- **Abregelung bei vollem Speicher:** SOLASI beobachtet bei vollen Speichern und Sonne, ob trotzdem eingespeist wird. Nach drei Minuten Einspeisung gilt die Abregelung als *nicht wirksam*, dann dürfen Verbraucher früher laufen
  und du bekommst eine Meldung. Bleibt der Zähler ausgeglichen, gilt sie als *bestätigt*.

## Zähler und Tagesverbrauch

Unter *Betrieb → Zähler* zeigst du weitere Zähler aus Home Assistant in SOLASI und in der Dashboard-Karte, zum Beispiel **Zählerstand Strom** (kWh) oder **Wasserzähler** (m³). Die Reihe steht ganz oben, getrennt vom Energiefluss.

- **Tagesverbrauch:** die große Kachel zeigt, was das Haus heute verbraucht hat. Sie lässt sich abschalten.
- **Zähler hinzufügen:** wähle den Sensor, gib Name, Symbol und Farbe an. Es sind bis zu acht Zähler möglich. Geeignet sind Sensoren, die nur hochzählen. Einheit und Nachkommastellen übernimmt SOLASI vom Sensor.
- **Verbrauch heute:** bei jedem Zähler lässt sich die Differenz zum Tagesbeginn anzeigen, zum Beispiel „+0,18 kWh heute“. **Wasserzähler** (Einheit m³, Symbol Wassertropfen oder „Wasser“ im Namen) zeigen den Verbrauch heute in **Litern** („+180 l heute“); der Zählerstand bleibt in m³. SOLASI merkt sich dafür den ersten Wert des Tages. Beim ersten Start mitten am Tag zählt der Verbrauch ab diesem Zeitpunkt. Wird ein Zähler getauscht oder zurückgesetzt, beginnt die Zählung neu.
- **Solarertrag und Netzbezug heute** lassen sich als weitere Kacheln dazuschalten.
- **Reihenfolge:** auf derselben Seite ordnest du alle Kacheln mit Pfeilen an. Die Karte übernimmt sie; mit `meters_order` (z. B. `[day, "m:sensor.wasser", pv, imp]`) bekommt eine Karte eine eigene Reihenfolge, im Editor mit Pfeilen. Steht der Tagesverbrauch an erster Stelle, wird er groß dargestellt, sonst sind alle Kacheln gleich groß.

## Blöcke anordnen

Unter *Einstellungen → Darstellung → Anordnung* legst du die Reihenfolge der Blöcke in **Übersicht** (Kennzahlen, Zähler, Energiefluss, Verlauf, Speicher, Überschuss, Protokoll) und **Statistik** (Zeitraum, Kennzahlen, Diagramm) fest. Mit den Pfeilen verschiebst du einen Block, mit dem Haken blendest du ihn aus. Die Anordnung wird mit *Speichern* abgelegt und gilt auf allen Geräten. *Standard wiederherstellen* setzt sie zurück. Auf breiten Bildschirmen verteilt SOLASI die Blöcke in der gewählten Reihenfolge auf zwei Spalten, am Handy stehen sie untereinander.

## Dashboard-Karte

SOLASI installiert beim Start die Karte `solasi-card` und trägt sie als Dashboard-Ressource ein. Unter **System → Dashboard-Karte** siehst du den Stand und findest bei Bedarf die manuelle Anleitung.

Alle Optionen lassen sich auch im visuellen Editor einstellen, die Reihenfolge der Blöcke mit Pfeilen unter den Schaltern. Ein Block, der nicht in `order` steht, kommt in Standardreihenfolge hinten dran; ausgeblendet wird weiter mit den `show_*`-Optionen. Der Not-Aus-Knopf erscheint nur, wenn der Schalter *Not-Aus* existiert, also mit MQTT.

Karte hinzufügen: Dashboard bearbeiten → *Karte hinzufügen* → **SOLASI** wählen, oder „Manuell“:

```yaml
type: custom:solasi-card
entity: sensor.solasi        # optional
title: SOLASI                # optional, "" blendet den Titel aus
show_headline: true          # Klartext-Überschrift
show_batteries: true         # Ladestand je Speicher
show_surplus: true           # Überschuss und Verbraucher
show_tags: true              # Eco, Zähler, Sollwert
size: large                  # large oder compact (vier Kacheln, ohne Diagramm)
show_meters: true            # Reihe mit Tagesverbrauch und Zählern ganz oben
meters_layout: big           # big (große Kachel links) oder even (alle gleich groß)
meters_order: []              # Reihenfolge der Zählerkacheln, leer = wie im Add-on
order: [meters, headline, flow, trend, batteries, surplus, tags]   # Reihenfolge der Blöcke (Standard wie hier)
show_trend: true             # Verlauf der letzten 24 Stunden
show_kill: true              # Not-Aus-Knopf mit Rückfrage (benötigt MQTT)
tap_open: true               # Antippen öffnet SOLASI
accent: ""                   # Akzentfarbe, z. B. "#3F5BD8"
```

**Entitäten für eigene Karten, Verläufe und Automationen:** `sensor.solasi` (Status, alle Werte als Attribute), `sensor.solasi_pv_power`, `sensor.solasi_house_power`, `sensor.solasi_battery_power`
(+ entlädt, − lädt), `sensor.solasi_target_power`, `sensor.solasi_surplus_power`, `sensor.solasi_base_load`. Mit einem MQTT-Broker ersetzt SOLASI sie durch feste Entitäten (siehe unten); ohne Broker sind es einfache Sensoren, die nach einem Neustart von Home Assistant sofort neu angelegt werden.

**Klappt die automatische Installation nicht?** Kopiere `solasi-card.js` nach `/config/www/solasi/` und trage unter *Einstellungen → Dashboards → ⋮ → Ressourcen* die URL `/local/solasi/solasi-card.js` als JavaScript-Modul ein
(dafür den erweiterten Modus im Benutzerprofil einschalten). Wurde der Ordner `www` neu angelegt, starte Home Assistant einmal neu.

## Feste Entitäten und Energie-Dashboard (MQTT)

Mit einem MQTT-Broker (am einfachsten das Add-on **Mosquitto broker**) legt SOLASI echte Entitäten in Home Assistant an. Sie bleiben nach einem Neustart erhalten, erscheinen in der Entitäten-Verwaltung, haben einen Verlauf und lassen sich im **Energie-Dashboard** verwenden.

**Einrichtung:** Mosquitto-Add-on installieren und starten, die MQTT-Integration bestätigen, SOLASI neu starten. Mehr ist nicht nötig, SOLASI findet den Broker selbst. Unter **System → Entitäten (MQTT)** siehst du, ob die Verbindung steht. Einen eigenen Broker trägst du dort ebenfalls ein.

Alle Entitäten gehören zum Gerät **SOLASI** (*Einstellungen → Geräte & Dienste → MQTT*):

| Art | Entitäten |
|---|---|
| Leistung (W) | Solarleistung, Hausverbrauch, Speicherleistung (+ entlädt, − lädt), Netzleistung (+ Bezug), Sollwert, Überschuss, Grundlast (gelernt) |
| Ladestand | Durchschnitt aller Speicher (%) |
| Energiezähler (kWh) | Solarertrag, Hausverbrauch, Netzbezug, Einspeisung, Speicher geladen, Speicher entladen. Sie zählen dauerhaft weiter und passen direkt ins Energie-Dashboard |
| Schalter | **Regelung**, **Testmodus**, **Not-Aus**. Damit schaltest du SOLASI auch aus Automationen, Szenen und Sprachassistenten |
| Hinweise | Zustand, Zählerproblem, Eco-Modus aktiv |

*Energie-Dashboard:* Unter *Einstellungen → Dashboards → Energie* kannst du Netzbezug, Einspeisung, Solarertrag und den Speicher (geladen/entladen) mit diesen Zählern verknüpfen. Die Zähler beginnen bei 0, sobald SOLASI sie das erste Mal liefert.

**Ohne MQTT** arbeitet SOLASI unverändert weiter: Die Karte, der Wächter und alle Funktionen laufen, und die Werte stehen als einfache Sensoren (`sensor.solasi_pv_power` usw.) bereit. Diese Sensoren sind nicht in der Entitäten-Verwaltung und fehlen nach einem Neustart von Home Assistant kurz. Sobald MQTT verbunden ist, werden sie durch die festen Entitäten ersetzt.

**Not-Aus als Schalter:** *An* stoppt SOLASI und gibt die Speicher frei, *Aus* setzt die Regelung fort. Der Zustand bleibt auch nach einem Neustart erhalten.

## Sicherung der Einstellungen

Unter *Einstellungen → Sicherheit & Meldungen → Sicherung der Einstellungen* lädst du alle Einstellungen als Datei herunter und spielst sie bei Bedarf wieder ein, zum Beispiel für eine neue Installation.
Die Einstellungen sind außerdem Teil der Home-Assistant-Backups.

## Häufige Fragen und Fehlersuche

**Kann ich SOLASI ausprobieren, ohne dass etwas passiert?**
Ja, mit dem **Testmodus**. SOLASI rechnet dann alles durch und schreibt ins Protokoll, was es senden würde, sendet aber nichts.

**Wie stoppe ich SOLASI schnell?**
Mit dem **⛔ Not-Aus** oben. Der Speicher geht auf 0 W und in den Rückfall-Modus. Mit **▶ Fortsetzen** läuft SOLASI weiter.

**Der Speicher zeigt „Leistung nicht verfügbar“.**
Das ist normal, solange er nicht im Modus für externe Steuerung ist. Sobald SOLASI live steuert, schaltet es ihn um. Im Testmodus bleibt der Zustand, wie er ist.

**SOLASI regelt nicht, der Sollwert bleibt 0 W.**
Prüfe der Reihe nach: Ist **Regelung** eingeschaltet? Ist der **Testmodus** noch an? Steht oben **Gestoppt**? Liegt der Netzbezug unter der Einschaltschwelle (voreingestellt 120 W)?
Ist der Ladestand unter dem Minimum oder greift der Eco-Modus? Der **Selbsttest** zeigt Fehler in der Einrichtung.

**„Solar“ zeigt „–“.**
Der gewählte PV-Sensor liefert gerade keinen Wert oder ist falsch gewählt. Vergleiche in der Sensorliste des Geräts mit der Hersteller-App.

**Hausverbrauch oder Speicherleistung weichen von der Hersteller-App ab.**
Öffne *System → Selbsttest → Energiebilanz* und prüfe Sensorauswahl und **Messart**. Kleine Abweichungen entstehen, weil Zähler und Speicher in unterschiedlichen Takten messen.

**Der Modus springt in der Hersteller-App immer wieder zurück.**
Das ist gewollt: SOLASI hält den Speicher im Modus für externe Steuerung. Nimm zum Umstellen vorher den **Not-Aus**, oder schalte unter *Regelung → Funktionen* „Externe Steuerung automatisch einschalten“ aus.

**Was passiert bei einem Neustart von Home Assistant oder SOLASI?**
SOLASI macht danach weiter. Ein gesetzter Not-Aus bleibt bestehen. Beim Beenden gibt SOLASI die Speicher frei, bei einem plötzlichen Absturz greift der Wächter.

**Kann ich Speicher verschiedener Hersteller mischen?**
Ja, jeder Speicher hat seinen eigenen Typ. SOLASI verteilt den Sollwert auf beide.

**Nach einem Update sieht die Oberfläche alt aus.**
Lade die Seite neu (`Strg + Umschalt + R`, auf dem Mac `Cmd + Umschalt + R`).

**Wo liegen meine Daten?**
Einstellungen, Statistik und gelernte Werte liegen im Datenordner des Add-ons und sind Teil der Home-Assistant-Backups.

**Ich habe einen Fehler gefunden oder eine Idee.**
Melde dich unter [github.com/DEIN-NAME/solasi/issues](https://github.com/DEIN-NAME/solasi/issues/new/choose). Bitte hänge Selbsttest und Protokoll an, aber keine Zugangsdaten.

## Datenschutz und Haftung

SOLASI läuft lokal und spricht nur mit deinem Home Assistant. Es gibt keine Cloud, kein Konto und keine Datenübertragung an Dritte.

Die Software steuert Hardware und wird **ohne Gewähr** bereitgestellt. Du nutzt sie auf eigene Verantwortung. Beachte die Einspeisegrenzen deiner Anlage, die Anmeldepflichten und die Vorgaben deines Netzbetreibers sowie die Hinweise deines Speicherherstellers.
SOLASI ist ein unabhängiges Projekt und steht in keiner Verbindung zu SolarAssistant (solar-assistant.io), zu Anker oder zu anderen Herstellern.
