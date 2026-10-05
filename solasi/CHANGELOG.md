# Änderungen

## 1.0.5
- **Werkzeuge für Windows:** `tools/sync_from_zip.ps1` und `tools/release.ps1` (PowerShell) spielen ein neues Paket ein und veröffentlichen es, ohne Bash, `unzip` oder Python.
- **`.gitattributes`:** einheitliche Zeilenenden (LF), damit Skripte und Konfigurationen auf Windows nicht mit falschen Zeilenenden ausgecheckt werden.
- Die App selbst ist unverändert gegenüber 1.0.4.

## 1.0.4
- **Externe Steuerung automatisch einschalten:** Sobald SOLASI live steuert, stellt es den Betriebsmodus des Speichers auf die Option für externe Steuerung
  (bei Anker „third_party_control“), auch wenn gerade nichts zu regeln ist. Vorher geschah das erst, wenn ein Sollwert anlag. Es passiert beim Start,
  beim Einschalten der Live-Steuerung, nach „Fortsetzen“ und wenn der Modus von außen verstellt wird (dann höchstens alle 30 Sekunden). Bei Speichern mit
  Fernsteuerungs-Schalter (z. B. RS485) wird dieser vorher eingeschaltet. Nicht erreichbare Entitäten werden übersprungen. Im Testmodus, bei „Regelung aus“,
  im Not-Aus-Zustand und bei Zählerausfall wird nichts geändert. Abschaltbar unter *Regelung → Funktionen*.

## 1.0.3
- **Energiefluss zeigt, wohin die Solarleistung geht:** Vorher endeten alle Linien sternförmig am Haus, es sah aus, als ginge die gesamte Solarleistung ins Haus
  und der Speicher würde vom Haus geladen. Jetzt gibt es eine eigene Linie **Solar → Speicher**. Beispiel: 780 W Solar, Speicher lädt 260 W, Netz 9 W Bezug →
  520 W Solar → Haus, 260 W Solar → Speicher, 9 W Netz → Haus. Jede Linie trägt ihren Wert. Beim Laden aus dem Netz läuft die Ladeleistung über das Haus in den Speicher.
  Gilt für die Weboberfläche und die Dashboard-Karte (neues Attribut `flows` an `sensor.solasi`).

## 1.0.2
- **Behoben: Beim ersten Einrichten fehlten die Vorschläge ab „Beim Stoppen: Modus setzen auf“.** Die Listen für Ladestand, Leistungs- und PV-Sensoren
  und die Rückfall-Optionen wurden nur gefüllt, wenn beim Aufbau der Seite schon eine Leistungs-Entität bzw. ein Betriebsmodus eingetragen war. Jetzt stehen
  sofort alle Sensoren zur Auswahl, und die Sensoren des Geräts rücken nach vorn, sobald du die Leistungs-Entität eintippst (ohne Neuladen). Die Rückfall-Optionen
  erscheinen, sobald der Betriebsmodus gewählt ist. Schlägt die Geräte-Abfrage fehl, bleiben alle Sensoren wählbar.

## 1.0.1
- **PV direkt ins Haus, auch bei leerem Speicher:** Liegt der Ladestand unter dem Minimum, darf der Speicher so viel abgeben, wie seine Module
  gerade liefern. Die Batterie wird dabei nicht entladen. Vorher blieb die PV in dem Fall ungenutzt, und das Haus zog aus dem Netz.
  Abschaltbar unter *Regelung → Funktionen*, braucht den PV-Sensor je Speicher.
- **Eco-Modus begrenzt nur noch den Batterieanteil:** Die Leistung der Module kommt zusätzlich zur Eco-Grenze direkt ins Haus.
- **Messart der Leistungssensoren (AC oder Batterie):** Bei Speichern mit PV an der Batterieseite (z. B. Anker) messen Lade- und Entladesensoren
  die Batterie, die Abgabe ins Haus ist Solar plus Batterie. Daraus wird der Hausverbrauch jetzt richtig berechnet (Beispiel: 540 W Solar,
  Batterie lädt 140 W → 400 W Hausverbrauch). „Automatisch“ erkennt Anker mit PV-Sensor.
- **Unbekannt ist nicht 0:** Ist ein Sensor nicht verfügbar, zeigen Übersicht und Karte „–“ statt „0 W“, und abhängige Werte (Haus) bleiben unbekannt.
- **Sensorliste je Gerät:** Unter *Einstellungen → Anlage* zeigt SOLASI die Sensoren desselben Geräts mit aktuellem Wert und schlägt sie in den Feldern vor.
- **Selbsttest:** neue Energiebilanz (Solar, Batterie, Abgabe, Netz, Haus) zum Vergleich mit der Hersteller-App und eine Warnung, wenn Lade-Sensoren
  nach Batterie- statt Netzleistung aussehen.

## 1.0.0
Erste Version.

- **Nulleinspeisung** für einen oder zwei Heimspeicher mit gemeinsamem Regler, Eco-Modus, Schwellen, SOC-Grenzen, Netzladen aus Fremd-Überschuss
  und Abregelung bei vollem Speicher.
- **Speichertypen:** Anker SOLIX (Betrag + Richtung), Zahl mit Vorzeichen, Modus + Leistungen, Ausgangslimit, eigenes Skript. Typen lassen sich mischen.
- **Überschusssteuerung** für bis zu drei Verbraucher, auch stufenlos für Wallbox und Heizstab, mit Sperre der Akku-Entladung.
- **Sicherheit:** Not-Aus-Knopf, optionaler Not-Aus-Schalter, automatischer Stopp bei Zählerausfall oder Befehlsfehlern, Freigabe der Speicher
  mit Rückfall-Modus (z. B. Eigenverbrauch) beim Stoppen und Beenden, automatisch angelegter Wächter in Home Assistant für den Absturz.
- **Selbsttest** (Systemprüfung und Abregelungs-Wächter), **Benachrichtigungen**, **Grundlast lernen**, **Statistik** und **Replay**.
- **Weboberfläche** mit Energiefluss, Experten-Schalter und einklappbaren Gruppen, **Dashboard-Karte** `custom:solasi-card` und Entitäten `sensor.solasi…`.
- Export und Import der Einstellungen.
