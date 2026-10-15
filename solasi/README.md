# SOLASI

**Nulleinspeisung und Energieregelung für Heimspeicher, direkt in Home Assistant.**

SOLASI steuert deinen Batteriespeicher so, dass dein Haus möglichst viel Solarstrom selbst verbraucht: kaum Einspeisung ins Netz, kaum Bezug aus dem Netz.
Es läuft lokal auf deinem Home Assistant, ohne Cloud und ohne Konto.

**Das kann SOLASI**

- Regelt einen oder zwei Speicher gemeinsam auf Nulleinspeisung, Solarstrom geht zuerst ins Haus
- Eco-Modus, der den Akku schont und die nächtliche Grundlast lernt
- Überschuss für Heizstab, Wallbox (stufenlos) und Schalter
- Anker SOLIX, Marstek und weitere Speichertypen, dazu ein eigenes Skript für alles Weitere
- Live-Übersicht mit Energiefluss, Dashboard-Karte, Statistik und „Was wäre wenn“-Replay
- Feste Entitäten per MQTT: Sensoren, Energiezähler für das Energie-Dashboard und Schalter (Regelung, Testmodus, Not-Aus)
- Sicherheit: Testmodus, Not-Aus, Rückfall auf den Modus des Herstellers, Wächter und Benachrichtigungen

**Erste Schritte**

1. Add-on **starten** und **In der Seitenleiste anzeigen** einschalten.
2. **SOLASI** in der Seitenleiste öffnen. Die Willkommensseite führt durch die Einrichtung.
3. Mit eingeschaltetem **Testmodus** beginnen: SOLASI rechnet dann alles durch, sendet aber nichts. Im Protokoll siehst du, was passieren würde.
4. Erst wenn alles plausibel aussieht, den Testmodus ausschalten.

Die ausführliche Anleitung findest du im Reiter **Dokumentation**.

**Wichtig:** SOLASI steuert echte Hardware. Nutzung auf eigene Verantwortung, ohne Gewähr. Beachte die Einspeisegrenzen deiner Anlage und die Vorgaben deines Netzbetreibers.
SOLASI ist ein unabhängiges Projekt und nicht mit SolarAssistant, Anker oder anderen Herstellern verbunden.
