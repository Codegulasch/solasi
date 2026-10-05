# Änderungen

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
