<p align="center"><img src="solasi/logo.png" alt="SOLASI" width="250"></p>

# SOLASI – Nulleinspeisung und Energieregelung für Heimspeicher

SOLASI ist ein Add-on für **Home Assistant**. Es steuert deinen Batteriespeicher so, dass dein Haus möglichst viel von dem Strom verbraucht, den deine
Solaranlage erzeugt: kaum Einspeisung ins Netz, kaum Bezug aus dem Netz. Alles läuft **lokal** auf deinem Home Assistant, ohne Cloud und ohne Konto.

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FCodegulasch%2Fsolasi)

## Was SOLASI kann

- **Nulleinspeisung:** Ein oder zwei Speicher werden gemeinsam so geregelt, dass der Netzzähler nahe null bleibt.
- **Solarstrom zuerst ins Haus:** Auch bei leerem Speicher geht die Solarleistung direkt ins Haus, ohne die Batterie zu entladen.
- **Eco-Modus:** Schont den Akku bei niedrigem Ladestand und lernt auf Wunsch die nächtliche Grundlast deines Hauses.
- **Überschuss nutzen:** Heizstab, Wallbox (stufenlos) oder beliebige Schalter laufen, wenn mehr Solarstrom da ist, als das Haus braucht.
- **Mehrere Speichertypen:** Anker SOLIX, Marstek und andere, dazu Wechselrichter-Limits und ein eigenes Skript für alles Weitere. Typen lassen sich mischen.
- **Live-Übersicht:** Energiefluss mit Solar, Speicher, Haus und Netz, dazu eine Karte für dein Dashboard.
- **Auswertung:** Tagesstatistik mit Autarkie und Ersparnis sowie ein „Was wäre wenn“-Replay mit deinen echten Verlaufsdaten.
- **Sicherheit:** Testmodus, Not-Aus-Knopf, automatischer Rückfall auf den eigenen Modus des Herstellers (z. B. Eigenverbrauch), ein Wächter, der bei einem
  Ausfall eingreift, Benachrichtigungen aufs Handy und ein Selbsttest, der deine Einrichtung prüft.

## Voraussetzungen

- **Home Assistant OS oder Supervised** (du hast einen Add-on-Store). Home Assistant Container und Core unterstützen keine Add-ons.
- Ein **Speicher mit Home-Assistant-Anbindung**, bei Anker die offizielle Integration [Anker Solix Official](https://github.com/anker-charging/ha-anker-solix-official).
- Ein **Sensor für die Netzleistung in Watt**, z. B. ein Lesekopf am Stromzähler oder ein Shelly EM (positiv = Bezug, negativ = Einspeisung).
- Empfohlen: ein **Sensor für die Solarleistung** je Speicher.

## Installation

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store → ⋮ (oben rechts) → Repositories** und diese Adresse hinzufügen:
   `https://github.com/Codegulasch/solasi` (oder den Knopf oben benutzen).
2. **SOLASI** öffnen, **Installieren** und **Starten**, dann **In der Seitenleiste anzeigen** einschalten.
3. SOLASI in der Seitenleiste öffnen. Die Willkommensseite führt durch die Einrichtung.

## Erste Schritte

1. **Zähler und Speicher auswählen** (*Einstellungen → Anlage*). Der Selbsttest unter *System* zeigt, ob alles passt.
2. **Testmodus eingeschaltet lassen** und **Regelung** einschalten. SOLASI rechnet dann alles durch, sendet aber nichts. Im *Protokoll* siehst du, was passieren würde.
3. Wenn die Werte plausibel sind, den **Testmodus ausschalten**. Ab jetzt steuert SOLASI deinen Speicher.
4. Mach dich vorher mit dem **Not-Aus** vertraut: Ein Klick stoppt SOLASI und gibt den Speicher an seinen eigenen Modus zurück.

Die ausführliche Anleitung steht in der [Dokumentation](solasi/DOCS.md), die du auch im Add-on unter **Dokumentation** findest.

## Unterstützte Speicher

| Speicher | Anbindung | Stand |
|---|---|---|
| Anker SOLIX Solarbank 4 E5000 Pro (auch zwei) | Anker Solix Official | im Praxiseinsatz entwickelt und getestet |
| Marstek (z. B. Venus), Speicher mit einer Leistungszahl mit Vorzeichen oder mit Modus und Leistungen | passende Home-Assistant-Integration | nach Herstellerbeschreibung umgesetzt, bisher nur in Simulationen getestet |
| Wechselrichter mit Leistungsbegrenzung (z. B. über OpenDTU) | Zahl für die Abgabe | wie oben |
| Alle anderen (z. B. Victron, Huawei, Sungrow) | eigenes Skript | wie oben |

Bei allem außer Anker bitte **zuerst im Testmodus beobachten** und gern eine Rückmeldung geben.

## Wichtige Hinweise

- **Teste immer zuerst im Testmodus.** SOLASI steuert echte Hardware.
- **Beachte die Einspeisegrenzen** deiner Anlage (z. B. 800 VA bei Steckersolargeräten) und die Vorgaben deines Netzbetreibers. Die Voreinstellung für die Gesamtabgabe ist bewusst vorsichtig.
- **Nutzung auf eigene Verantwortung.** Die Software wird ohne Gewähr bereitgestellt (siehe [Lizenz](LICENSE)).
- **Datenschutz:** SOLASI spricht nur mit deinem Home Assistant. Es werden keine Daten an Dritte gesendet.

## Hilfe und Rückmeldung

- Öffne unter **System → Selbsttest** die Systemprüfung, sie nennt Fehler in der Einrichtung mit Lösungsvorschlag.
- Das **Protokoll** unter *System* zeigt, was SOLASI getan hat.
- Findest du einen Fehler oder hast du eine Idee, [melde dich hier](https://github.com/Codegulasch/solasi/issues/new/choose). Bitte hänge Selbsttest und Protokoll an, aber keine Zugangsdaten.

## Über das Projekt

**SOLASI** steht für **SOL**ar-**A**nlagen-**S**peicher-**I**nterface. Das Projekt ist unabhängig und steht in keiner Verbindung zu *SolarAssistant* (solar-assistant.io), zu Anker
oder zu anderen Herstellern. Die Regelstrategie orientiert sich am Forum-Blueprint „Anker SOLIX 4 Pro – Lokale Nulleinspeisung & Eco-Modus“ von MBP996 im Home-Assistant-Forum.
Der Code ist eine eigene Umsetzung. Freie Software unter der [MIT-Lizenz](LICENSE).

Entwickler finden Hinweise zum Mitmachen in [DEVELOPMENT.md](DEVELOPMENT.md).
