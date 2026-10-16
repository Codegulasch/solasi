# Änderungen

## 1.4.1
- **Energiefluss bei zwei Anlagen:** Jede Solaranlage steht jetzt mit ihrem eigenen Speicher als Paar da (HÜTTE links, DACH rechts, Netz und Haus in der Mitte). Je Anlage gibt es drei Linien: Solar → eigener Speicher (Ladeleistung), Solar → Haus und Speicher → Haus. Vorher gab es nur eine Sammellinie „Solar → Speicher“, die immer beim ersten Speicher endete.
## 1.4.0
- **Gesamt-Ladestand nach Kapazität:** Der „mittlere Ladestand“ ist jetzt nach der nutzbaren Kapazität der Speicher gewichtet (bisher einfacher Durchschnitt) und steht zusätzlich in kWh („6,2 von 15 kWh“). Die Kapazität trägst du je Speicher unter *Einrichtung* ein (zum Beispiel 5 und 10). Vorher stand sie nur im Experten-Modus.
- **Energiefluss mit zwei Anlagen:** Bei zwei Speichern zeigt der Energiefluss jede Solaranlage und jeden Speicher als eigene Kachel, mit Leistung, Ladestand und kWh. Das Design bleibt unverändert. Mit nur einem Speicher sieht alles aus wie bisher.
- **Verlauf:** Eine zusätzliche Fläche „aus Speichern“ zeigt, wann die Akkus ans Haus abgegeben haben (gilt für Add-on und Karte; der Verlauf füllt sich ab jetzt, ältere Punkte haben keinen Speicherwert).
- **Speicherliste und Karte:** Ladestand je Speicher auch in kWh.
- **Nur beobachten:** Neue Option je Speicher. SOLASI liest Ladestand und Leistung und zeigt sie an, schreibt aber nichts auf den Speicher und rechnet ihn nicht in den eigenen Sollwert ein. Gedacht für Speicher, die ihre Hersteller-App selbst regelt (zum Beispiel Anker mit Smart Meter und Nullexport).
## 1.3.5
- **Zwei Speicher mit unterschiedlichen Grenzen:** SOLASI beachtet jetzt das Maximum der Leistungs-Entität (z. B. 800 W bei der Anker Solix 4). Früher forderte es bei höherer eingestellter Entladeleistung (z. B. 1250 W) vom ersten Speicher mehr, als er annimmt, und verteilte den Rest nicht auf den zweiten.
## 1.3.4
- **Springen, dritte Runde:** Die Karte behält jetzt ihr `ha-card`-Element dauerhaft und tauscht nur den Inhalt, sodass die Karte nie für ein Bild leer steht. Zusätzlich hält der Kartenrahmen seine Mindesthöhe.
- **Versionshinweis:** Ist die Kartendatei im Browser oder in der App älter als das Add-on (zwischengespeichert), zeigt die Karte einen Hinweis „Karte veraltet – Seite neu laden“.
- **Sprung-Diagnose** der Karte (Option `debug: true`) zeigt Version und letzte Ereignisse.
## 1.3.3
- **Springen behoben (Dashboard):** Aus einer Bildschirmaufnahme ließ sich die Ursache eingrenzen: Die Seite wurde für einen Moment kürzer, der Browser kappte die Scrollposition und die Ansicht sprang in einem Bild nach oben. Jetzt gibt es zwei Absicherungen. Die Karte merkt sich ihre Höhe je Fensterbreite schon vor dem ersten Zeichnen und fällt nicht mehr zusammen, auch nicht, wenn Home Assistant sie neu erzeugt oder der Sensor kurz „nicht verfügbar“ meldet (dann bleibt der letzte Stand abgeblendet stehen). Ein **Scroll-Wächter** holt die alte Position zurück, falls die Seite ohne Eingabe nach oben springt und dabei am unteren Ende landet.
## 1.3.2
- **Statistik je Kachel:** Antippen einer Kachel in der Übersicht öffnet eine eigene Seite mit Verlauf (7, 30 oder 90 Tage), Summe, Durchschnitt und höchstem Tag. Zähler holen die Tageswerte aus der Langzeitstatistik von Home Assistant, ersatzweise aus dem Recorder-Verlauf; Wasser steht in Litern. Tagesverbrauch, Solarertrag und Netzbezug nutzen die SOLASI-Statistik.
- **Karte:** Antippen einer Zählerkachel öffnet Verlauf und Statistik des Zählers in Home Assistant, alle anderen Kacheln öffnen weiter SOLASI.
- **Gegen das Springen:** jeder Block der Übersicht wird nie niedriger als zuvor (bei gleicher Breite), sodass die Seite nicht schrumpft und der Browser die Scrollposition nicht verschiebt. Die Karte meldet Home Assistant ihre echte Höhe (`getCardSize`), damit das Dashboard-Layout nicht nachträglich nachrückt.
- **Sprung-Diagnose:** unter *Einstellungen → Darstellung* einschaltbar. Blendet unten links ein, wenn die Seite ohne Eingabe nach oben springt oder sich Elemente verschieben, und nennt die Ursache. Gedacht, um einen hartnäckigen Sprung gezielt zu finden.
## 1.3.1
- **Zählerkacheln anordnen:** unter *Betrieb → Zähler → Reihenfolge der Kacheln* (Tagesverbrauch, jeder Zähler, Solarertrag, Netzbezug). In der Karte gilt dieselbe Reihenfolge, oder eine eigene mit `meters_order` (im Editor mit Pfeilen). Steht der Tagesverbrauch ganz oben, bleibt er die große Kachel.
## 1.3.0
- **Blöcke anordnen:** *Einstellungen → Darstellung → Anordnung* legt die Reihenfolge der Blöcke in **Übersicht** und **Statistik** fest (Pfeile, Haken zum Ausblenden, „Standard wiederherstellen“). Die Anordnung wird im Add-on gespeichert und gilt auf allen Geräten.
- **Dashboard-Karte:** neue Option `order` und im visuellen Editor Pfeile zum Verschieben der Blöcke. Bestehende Karten sehen unverändert aus; `show_*` blendet weiter aus.
- **Wasser in Litern:** der Verbrauch heute aller Wasserzähler (m³) wird als „+180 l heute“ angezeigt, in Add-on und Karte. Der Zählerstand bleibt in m³.
- **Kein Springen mehr:** die Übersicht baute bisher alle 2 Sekunden alles neu auf, dabei sprang die Seite beim Scrollen, und geöffnete *Technische Details* klappten wieder zu. Jetzt werden nur geänderte Blöcke aktualisiert, die Scrollposition wird bei Höhenänderungen ausgeglichen, und während des Scrollens wird nicht neu gezeichnet. Die Karte hält ihre Höhe (auch beim Laden) und zeichnet nur bei geändertem Inhalt.

## 1.2.2
- **Zählerreihe in Übersicht und Dashboard-Karte:** eine eigene Reihe ganz oben, getrennt vom Energiefluss. Sie zeigt den **Tagesverbrauch** (Haus heute) und beliebige **Zähler** aus Home Assistant, zum Beispiel Zählerstand Strom oder Wasserzähler.
  Bei jedem Zähler lässt sich der **Verbrauch heute** einblenden („+0,18 m³ heute“). SOLASI merkt sich dafür den Stand zu Beginn des Tages. Optional kommen Solarertrag und Netzbezug heute dazu.
- **Neue Seite *Betrieb → Zähler*:** Sensor, Name, Symbol und Farbe je Zähler, bis zu acht Zähler, mit Vorschau.
- **Karte:** neue Optionen `show_meters` und `meters_layout` (große Kachel links oder alle gleich groß), auch im visuellen Editor.
- Die Zählerreihe passt sich der Breite an: in schmalen Karten stehen die Kacheln untereinander.
- Mehr Abstand zwischen Zählerreihe und Energiefluss.
## 1.2.1
- **Neue Energiefluss-Grafik** in der Übersicht und in der Dashboard-Karte, beide aus demselben Code und deshalb gleich: Kacheln mit eigenen Symbolen (Sonne, Akku mit Ladestand, Haus, Netzmast), weiche Kurven statt Winkeln, wandernde Punkte in Flussrichtung und Linien, die mit der Leistung dicker werden.
- **Verlauf der letzten 24 Stunden** (Solar als Fläche, Haus als Linie, aktueller Wert als Punkt) in der Übersicht und in der Karte. Die Zeitachse nutzt jetzt echte Uhrzeiten.
- **Überschrift aus dem Energiefluss:** z. B. „Solar versorgt dein Haus und lädt den Speicher“ statt nur nach dem Sollwert.
- **Speicher-Karte** in Klartext („80 % geladen · gibt 270 W ab“, „Extern gesteuert“). Die Rohwerte stehen unter *Technische Details*.
- **Protokoll in der Übersicht** ruhiger gestaltet.
## 1.2.0
- **Neues Layout:** Seitenleiste mit den Bereichen *Betrieb*, *Auswertung* und *System*, dazu eine Kopfleiste mit Status, **Regelung**, **Testmodus** und **Not-Aus** (mit Rückfrage). Das Design bleibt gleich.
- **Neue Übersicht:** Kennzahlen, Energiefluss, Speicher, Überschuss und Protokoll auf einen Blick, plus ein Hinweisband, wenn etwas Aufmerksamkeit braucht.
- **Am Handy:** Leiste unten mit den wichtigsten Seiten und einem „Mehr“-Menü für den Rest.
- **Einstellungen** mit eigener Navigation: *Regelung*, *Sicherheit & Meldungen* und *Darstellung* (Startseite und Dichte, je Gerät gemerkt).
- **Einrichtungsassistent** im neuen Layout; beim ersten Start ist die Seitenleiste ausgeblendet. Die Schritte *Solar* und *Haus* sind zu **Solar und Haus** zusammengefasst.
- **Dashboard-Karte:** Größen *Groß* und *Kompakt*, Tagesverlauf der letzten 24 Stunden, Not-Aus-Knopf mit Rückfrage (benötigt MQTT), Antippen öffnet SOLASI, Akzentfarbe und ein visueller Editor.

## 1.1.0
- **Echte Entitäten über MQTT:** Mit einem MQTT-Broker (z. B. dem Mosquitto-Add-on) legt SOLASI ein Gerät „SOLASI“ mit festen Entitäten an: Leistungen, Ladestand, Zustand, **Energiezähler für das Energie-Dashboard** und die Schalter **Regelung**, **Testmodus** und **Not-Aus**.
  Die Entitäten bleiben nach einem Neustart erhalten und haben einen Verlauf. Ohne Broker läuft alles wie bisher. Neue Seite *System → Entitäten (MQTT)* und ein Eintrag im Selbsttest.
- Dauerhafte Gesamtzähler (kWh) für Solarertrag, Verbrauch, Netzbezug, Einspeisung und Speicher.
- Hinweis: Die Regelgenauigkeit wurde im Simulator mit verschiedenen Reglern verglichen. Die bisherige Regelung liegt bereits nahe am Optimum, deshalb bleibt sie unverändert.
  Eine größere *Schrittweite* (z. B. 30 W) spart rund ein Viertel der Schreibzugriffe auf den Speicher bei nur etwa 3 % mehr Abweichung.

## 1.0.7
- **Not-Aus und Freigabe sind zuverlässiger:** Beim Stoppen sendet SOLASI jetzt immer 0 W und den Rückfall-Modus an den Speicher, auch wenn der zuletzt bekannte Zustand schon zu passen scheint.
  Direkt nach einem Befehl meldet das Gerät seinen neuen Zustand oft verzögert. Dann hätte SOLASI die Leistung stehen lassen können, obwohl der Speicher noch lief. Gilt für alle Speichertypen.

## 1.0.6
- Neue, ausführliche **Anleitung** in Home Assistant (Reiter „Dokumentation“) mit Einrichtung Schritt für Schritt, Sicherheit und Fehlersuche.
- Überarbeitete Kurzbeschreibung im Add-on-Store.

## 1.0.5
- Keine Änderungen an der App.

## 1.0.4
- **Externe Steuerung automatisch einschalten:** Sobald SOLASI live steuert, stellt es den Betriebsmodus des Speichers auf externe Steuerung (bei Anker „third_party_control“),
  auch wenn gerade nichts zu regeln ist. Das geschieht beim Start, beim Einschalten der Live-Steuerung, nach „Fortsetzen“ und wenn der Modus von außen verstellt wird
  (dann höchstens alle 30 Sekunden). Bei Speichern mit Fernsteuerungs-Schalter wird dieser vorher eingeschaltet. Im Testmodus, bei „Regelung aus“, im Not-Aus-Zustand und bei
  Zählerausfall wird nichts geändert. Abschaltbar unter *Regelung → Funktionen*.

## 1.0.3
- **Der Energiefluss zeigt, wohin die Solarleistung geht:** Es gibt jetzt eine eigene Linie *Solar → Speicher*. Beispiel: 780 W Solar, Speicher lädt 260 W, Netz 9 W Bezug →
  520 W Solar → Haus, 260 W Solar → Speicher, 9 W Netz → Haus. Jede Linie trägt ihren Wert. Beim Laden aus dem Netz läuft die Ladeleistung über das Haus in den Speicher.
  Gilt für die Oberfläche und die Dashboard-Karte.

## 1.0.2
- **Behoben:** Beim ersten Einrichten fehlten die Vorschläge ab „Beim Stoppen: Modus setzen auf“. Jetzt stehen sofort alle Sensoren zur Auswahl, und die Sensoren des Geräts
  rücken nach vorn, sobald du die Leistungs-Entität eintippst. Die Rückfall-Optionen erscheinen, sobald der Betriebsmodus gewählt ist.

## 1.0.1
- **Solarstrom direkt ins Haus, auch bei leerem Speicher:** Liegt der Ladestand unter dem Minimum, darf der Speicher so viel abgeben, wie seine Module gerade liefern.
  Die Batterie wird dabei nicht entladen. Abschaltbar unter *Regelung → Funktionen*.
- **Der Eco-Modus begrenzt nur noch den Anteil aus der Batterie.** Die Solarleistung kommt zusätzlich direkt ins Haus.
- **Messart der Leistungssensoren (AC oder Batterie):** Bei Speichern mit Solar an der Batterieseite (z. B. Anker) wird der Hausverbrauch jetzt richtig berechnet.
- **Unbekannt ist nicht 0:** Ist ein Sensor nicht verfügbar, zeigen Übersicht und Karte „–“ statt „0 W“.
- **Sensorliste je Gerät** in den Einstellungen mit aktuellen Werten zum Abgleich mit der Hersteller-App.
- **Selbsttest:** neue Energiebilanz und eine Warnung, wenn Lade-Sensoren nach Batterie- statt Netzleistung aussehen.

## 1.0.0
Erste Version.

- Nulleinspeisung für einen oder zwei Heimspeicher mit gemeinsamem Regler, Eco-Modus, Schwellen, Ladestandsgrenzen, Laden aus Fremd-Überschuss und Abregelung bei vollem Speicher.
- Speichertypen: Anker SOLIX, Zahl mit Vorzeichen, Modus + Leistungen, Ausgangslimit, eigenes Skript. Typen lassen sich mischen.
- Überschusssteuerung für bis zu drei Verbraucher, auch stufenlos für Wallbox und Heizstab.
- Sicherheit: Not-Aus-Knopf, optionaler Not-Aus-Schalter, automatischer Stopp bei Zählerausfall oder Befehlsfehlern, Freigabe der Speicher mit Rückfall-Modus beim Stoppen und Beenden,
  automatisch angelegter Wächter in Home Assistant.
- Selbsttest, Benachrichtigungen, Grundlast lernen, Statistik und Replay.
- Weboberfläche mit Energiefluss, Experten-Schalter und einklappbaren Gruppen, Dashboard-Karte `solasi-card` und Entitäten `sensor.solasi…`.
- Export und Import der Einstellungen.
