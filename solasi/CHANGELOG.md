# Änderungen

## 2.2.0
- **Haus-Ansicht:** Unter Einstellungen → Darstellung lässt sich der Energiefluss als Haus in Schrägansicht anzeigen (gilt auch für die Dashboard-Karte). Das Haus trägt die erste Solaranlage auf dem Dach, weitere Anlagen stehen aufgeständert vor dem Haus; jeder Speicher ist ein Schrank mit Ladestand, das Netz ein Mast. Der Fluss läuft als gleichmäßig wandernde Punkte entlang der Wege, mit Watt-Angabe je Weg.
- **Phasen (3-phasiger Zähler):** Neue Seite unter Betrieb. Leistung, Spannung und Strom je Phase (z. B. Shelly 3EM), Schieflast, Auslastung der Sicherung mit Warnung. Der Gesamtzähler bleibt unverändert.
- **Einspeise-Phase wird erkannt:** SOLASI vergleicht die Leistungssprünge der Speicher mit den Änderungen je Phase und zeigt, auf welcher Phase eingespeist wird (mit Sicherheit in %). Manuell festlegbar, „Neu messen“ beginnt von vorn.

## 2.1.0
- **Modi sichtbar und erklärt:** Der aktive Modus steht in der Kopfzeile und als Tag auf der Dashboard-Karte. Die Übersicht zeigt die „Wirkung“ (Gibt ab bis X %, lädt bis Y %, je Speicher). Neu: „So arbeitet SOLASI“ unter Ziele mit Tabelle aller Modi und den Formeln.
- **Stromfresser:** Neue Seite unter Auswertung. Zeichnet Messsteckdosen auf (10 s / 1 min), Rangliste mit kWh, Anteil, €/Jahr, Standby und „nicht gemessen“, Filter nach Zeitraum, Uhrzeit und Wochentagen, Leistungskurve mit Vergleich zu gestern. Optional Phase je Gerät (Vorbereitung für 3-Phasen).
- **Entfernt:** Suche (Strg+K) und Demo-Modus.
- **Korrektur:** Kacheln in „Heute und Zähler“ brechen bei schmaler Breite nicht mehr mitten im Wort um.

## 2.0.1
- **Korrektur:** Auf der Übersicht überlappten sich die Kennzahlen-Kacheln mit der Karte darunter (Abstand ging verloren). Abstand ist wieder da.
- **Eigener Port wie bei PrintDock:** Ohne Konto ist der Port offen (jeder im Netzwerk gilt als Besitzer). Sobald das erste Konto existiert, verlangt er eine Anmeldung. Die Konten-Seite weist darauf hin, solange der Port offen ist.
- **Demo-Modus:** Unter Einstellungen → Ansicht (und auf der Startseite vor der Einrichtung) lässt sich SOLASI mit simulierten Werten ansehen. Solange Demo an ist, steuert SOLASI nichts.
- Suche: Antworten aus dem Protokoll zeigen jetzt die Uhrzeit korrekt an.

## 2.0.0
- **Neue Oberfläche:** Menü in Betrieb / Auswertung / System, Einstellungen als Übersicht mit Themen, Änderungsleiste mit „Verwerfen“. Energiefluss, Statistik und alle bisherigen Seiten bleiben. Unter Einstellungen → Ansicht gibt es „Klassische Ansicht“ als Weg zurück.
- **Modi und Ziele:** fünf Modi zur Schnellwahl (Ausgewogen, Autark, Akku schonen, Urlaub, Notfall) plus eigene Modi. Drei Regler (Reserve, Genauigkeit, Akku schonen) berechnen die Einzelwerte; jeder Einzelwert bleibt von Hand änderbar und wird dann als „angepasst“ markiert.
- **Speicher:** Liste links, Einstellungen je Speicher in Reitern (Verbindung, Grenzen, Leistung, Umladen, Erweitert), Aktiv/Wartung/Aus. Bis zu vier Speicher; die Aufteilung funktioniert jetzt auch mit mehr als zwei.
- **Geräte-Erkennung:** „Speicher hinzufügen“ sucht in Home Assistant nach passenden Geräten und füllt die Felder vor (oder von Hand).
- **Gesundheit:** To-do-Liste mit „Beheben“-Knöpfen, die direkt zur richtigen Einstellung springen.
- **Suche (Strg+K):** Seiten, Modi, Befehle („Reserve auf 40 %“) und Fragen, die aus dem Protokoll beantwortet werden.
- **Automatik:** Zeitpläne und Wenn-dann-Regeln (Uhrzeit, Ladestand, Netzbezug, Solarleistung → Modus wechseln oder Meldung senden) und ein Wochenbericht per Meldung.
- **Konten und eigener Port:** Konten mit Rollen (Besitzer, Mitbewohner, Nur lesen), Passwörter mit scrypt gespeichert, Sperre nach Fehlversuchen. Der direkte Zugang auf Port 8100 ist standardmäßig aus (im Add-on unter Netzwerk einen Port eintragen) und verlangt immer eine Anmeldung.
- Umladen zwischen Speichern wird im Protokoll vermerkt („A gibt ab – B lädt … W“).

## 1.7.2
- **Umladen als „durchgereicht“:** Lädt ein Speicher per AC den anderen, steht diese Leistung im gemessenen Hausverbrauch. Jetzt zeigt die Hauskachel den echten Verbrauch („+340 W Laden“), die Linie zum ladenden Speicher trägt „durchgereicht“, und die Überschrift sagt „durchgereicht, kein Mehrverbrauch“. Auch Tagesverbrauch, Vergleich mit gestern, Autarkie und die Grundlast-Lernfunktion rechnen die durchgereichte Leistung heraus (ab diesem Update). Unter 10 W wird nichts angezeigt. Abschaltbar unter *Darstellung → Energiefluss*, in der Karte mit `flow_passthrough: false`.
- **Solar gesamt im Energiefluss:** Die Linien verlassen die Kachel „Solar gesamt“ jetzt seitlich nach links und rechts und laufen von oben in die Anlagen. Das gibt ein runderes Gesamtbild.

## 1.7.1
- **Überschuss in anderen Speicher umladen:** Ist ein Speicher voll und kann ein anderer per AC laden (Schalter „Laden aus dem Netz“ an, Leistungsfluss-Option „Netz-zu-Batterie-Ladeleistung“), regelt SOLASI den vollen nicht mehr ab. Seine Solarleistung geht ins Haus, der Rest als Einspeisung ins Netz, und der andere Speicher lädt diesen Überschuss, sobald er über der Einschaltschwelle liegt. Die Überschrift lautet dann „Überschuss von HÜTTE lädt DACH mit 340 W“, im Energiefluss läuft die Linie vom Haus zum ladenden Speicher. Sind alle Speicher voll, wird wie bisher abgeregelt. Abschaltbar unter *Funktionen → Überschuss in anderen Speicher umladen*. Hinweis: Beim Umladen über Wechselrichter und Netzanschluss gehen etwa 10–15 % verloren.
- **Notstromreserve:** Neue optionale Entität je Speicher (nur lesen). SOLASI behandelt sie wie die Entladegrenze: Mindest-Ladestand ist der höchste Wert aus eigenem Minimum, Entladegrenze und Notstromreserve. Der Selbsttest zeigt sie an.
- **Leistungsgrenzen automatisch:** Hat die Leistungssteuerung die Attribute `max_charge_power` und `max_discharge_power` (Anker), liest SOLASI die Grenzen daraus, wenn keine eigene Entität eingetragen ist.

## 1.7.0
- **Speicher aktiv, in Wartung oder deaktiviert:** Neu je Speicher (*Einrichtung → Betrieb*) und als Home-Assistant-Entität „… Betrieb“ (Aktiv, Wartung, Deaktiviert). **Wartung** graut den Speicher im Energiefluss aus, SOLASI steuert, liest und prüft ihn nicht und meldet keine Fehler. **Deaktiviert** blendet ihn aus, als gäbe es ihn nicht. Beim Wechsel gibt SOLASI den Speicher an sein eigenes Regelverhalten zurück (Rückfall-Modus), beim Zurückschalten übernimmt es ihn sofort wieder. Der Selbsttest überspringt solche Speicher.
- **Automatische Wartung:** Antwortet der Ladestand eines Speichers 2 Minuten lang nicht (Entität weg, umbenannt, nicht erreichbar), geht er von selbst in Wartung, statt Fehler zu erzeugen. Kommt er zurück, läuft er nach 30 Sekunden wieder mit. Abschaltbar unter *Sicherheit*.
- **Energiefluss wächst mit der Breite:** Auf PC und Tablet wird die Zeichnung breiter und rückt die Kacheln auseinander, am Handy bleibt alles wie bisher. Neue Einstellung „Größe“ (Automatisch, Kompakt, Groß), in der Karte `flow_size`. Die Höhenbegrenzung der Zeichnung ist entfallen.
- **Farbverlauf nur hinter Überschrift und Energiefluss:** Wie in der Übersicht des Add-ons liegt der Verlauf jetzt auf einem eigenen Block, nicht mehr hinter der ganzen Karte.
- **Karte im Add-on einstellen:** *Einstellungen → Darstellung → Dashboard-Karte*: Überschrift, Zählerreihe, Tagesverlauf, Speicher, Überschuss, Hinweise, Not-Aus-Knopf und Farbverlauf ein- und ausblenden, Größe, Zähleranordnung, Akzentfarbe und Reihenfolge der Blöcke. Gilt für alle Karten. Optionen in der Karte selbst gehen vor; der Karteneditor speichert nur noch Werte, die vom Standard abweichen.
- **Vergleich mit gestern:** In den Heute-Kacheln (Tagesverbrauch, Solar, Netzbezug, Aus Speichern und eigene Zähler) steht eine Zeile wie „gestern 5,8 kWh · ▲ 12 %“. Verglichen wird standardmäßig mit gestern **bis zur gleichen Uhrzeit** (SOLASI merkt sich dafür Stundenstände), bis diese vorliegen mit dem ganzen Tag. Mehr Solar ist grün, mehr Netzbezug rot, der Rest neutral. Einstellbar unter *Zähler* (Gleiche Uhrzeit, Ganzer Tag, Aus), in der Karte mit `meters_compare`.

## 1.6.0
- **Grenzen in den Speicher schreiben:** Neu je Speicher (*Einrichtung*): „Eigener Mindest-Ladestand“, „Eigener Höchst-Ladestand“ (leer = globaler Wert) und der Schalter „Grenzen in den Speicher schreiben“. Ist er an, schreibt SOLASI den Mindest-Ladestand in die Entladegrenze und den Höchst-Ladestand in die Ladeobergrenze des Speichers und setzt sie zurück, wenn sie sich ändern (auch durch die Anker-App), höchstens alle 5 Minuten. Werte werden an Minimum, Maximum und Schrittweite der Entität angepasst; was geändert wurde, steht im Protokoll. Im Testmodus wird nur protokolliert, beobachtete Speicher werden nie beschrieben. Der Selbsttest zeigt Soll und Ist.
- **Energiefluss mit Gesamt-Solar oben:** Bei zwei Anlagen steht oben in der Mitte die Solarleistung aller Anlagen, die sich auf die beiden Solar-Kacheln verteilt.
- **Energiefluss einstellbar:** *Einstellungen → Darstellung → Energiefluss*: Vorlage (Gesamt-Solar oben, Paare, Kompakt), Kacheln einzeln ein- und ausblenden (Solar gesamt, Solar je Anlage, Speicher, Netz, Haus), Netz in der Mitte oder neben dem Haus, Reihenfolge der Anlagen. Die Karte übernimmt das; mit den Optionen `flow_layout`, `flow_hide`, `flow_grid_pos` und `flow_order` (oder im Karteneditor) lässt es sich je Karte überschreiben. Bei mehr als zwei Anlagen gelten Reihenfolge sowie Netz und Haus.

## 1.5.1
- **Farbverlauf in der Dashboard-Karte:** Die Karte hat jetzt denselben sanften Verlauf wie die Übersicht im Add-on (Akzentfarbe oben links, läuft in die Kartenfarbe aus). Er folgt der Karten-Option `accent` und passt sich Hell- und Dunkelmodus an. Mit `gradient: false` (oder im Editor „Farbverlauf im Hintergrund“) bleibt die Karte einfarbig.

## 1.5.0
- **Überschrift zeigt, was wirklich fließt:** Bisher stand dort bei Flüssen unter 5 W der Sollwert („Die Speicher versorgen dein Haus mit 339 W“), obwohl das Netz das Haus versorgte. Jetzt kommt der Text aus den echten Flüssen. „Überschuss lädt …“ steht nur noch, wenn wirklich nichts aus dem Netz kommt; sonst „Solar lädt den Speicher mit 80 W“ und „Haus bezieht 511 W aus dem Netz“.
- **Speicher-Kacheln:** Statt zweimal derselben Wattzahl zeigt die Kachel „lädt“ oder „entlädt“, bei Ruhe „bereit“, bei vollem Speicher „voll“.
- **Entladegrenze und Ladeobergrenze:** Neue optionale Entitäten je Speicher (*Einrichtung*). SOLASI richtet sich nach der Entladegrenze des Speichers (der höhere Wert aus Entladegrenze und eigenem Mindest-Ladestand) und sieht den Speicher ab der Ladeobergrenze als voll. Der Selbsttest zeigt die wirksamen Werte.
- **Speicher, der nichts liefert:** Gibt ein Speicher trotz Anforderung etwa 90 Sekunden nichts ab (zum Beispiel an einer Grenze im Gerät), bekommt er vorerst keinen Anteil, die Kachel zeigt „Grenze“, und der andere Speicher übernimmt.
- **Aus Speichern heute:** Neue Kachel in der Heute-Reihe (bei „Solarertrag, Netzbezug und Speicher heute dazu“), mit der geladenen Menge darunter, antippbar für den Verlauf. Das Tagesdiagramm in der Statistik hat eine Reihe „Aus Speichern“.
- **Menü am Handy:** Die Schnellleiste steht jetzt oben (mit Statistik) und öffnet „Mehr“ von oben. Unten verschwand sie bei manchen Geräten hinter der Browserleiste.
- **README** ist jetzt rein für Anwender geschrieben, mit häufigen Fragen. Technisches steht in DEVELOPMENT.md.

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
