<p align="center"><img src="solasi/logo.png" alt="SOLASI" width="250"></p>

# SOLASI – Nulleinspeisung und Energieregelung für Heimspeicher

🇬🇧 [English version](README.en.md)

> **🧪 Beta:** SOLASI ist noch in der Beta-Phase. Es wurde an einer Anlage mit Anker SOLIX (Solarbank 4) entwickelt und im Alltag erprobt; andere Speichertypen sind nach den Beschreibungen ihrer Integrationen umgesetzt und bisher nur in Simulationen geprüft. Es steuert echte Hardware, Fehler sind möglich. Fang immer im **Testmodus** an, behalte den **Not-Aus** im Blick und prüfe neue Funktionen (zum Beispiel Netz-Laden und Entladesperre) zuerst mit kurzen Versuchen. Die Nutzung erfolgt auf eigene Verantwortung. Rückmeldungen und Fehlerberichte sind willkommen.

SOLASI ist ein Add-on für **Home Assistant**. Es steuert deinen Batteriespeicher so, dass dein Haus möglichst viel von dem Strom verbraucht, den deine
Solaranlage erzeugt: kaum Einspeisung ins Netz, kaum Bezug aus dem Netz. Alles läuft **lokal** auf deinem Home Assistant, ohne Cloud und ohne Konto.

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDEIN-NAME%2Fsolasi)

## Was SOLASI kann

- **Nulleinspeisung:** Ein oder zwei Speicher werden gemeinsam so geregelt, dass der Netzzähler nahe null bleibt.
- **Solarstrom zuerst ins Haus:** Auch bei leerem Speicher geht die Solarleistung direkt ins Haus, ohne die Batterie zu entladen.
- **Eco-Modus:** Schont den Akku bei niedrigem Ladestand und lernt auf Wunsch die nächtliche Grundlast deines Hauses.
- **Überschuss nutzen:** Heizstab, Wallbox (stufenlos) oder beliebige Schalter laufen, wenn mehr Solarstrom da ist, als das Haus braucht.
- **Mehrere Speichertypen:** Anker SOLIX, Marstek und andere, dazu Wechselrichter-Limits und ein eigenes Skript für alles Weitere. Typen lassen sich mischen.
- **Live-Übersicht:** Energiefluss mit Solar, Speicher, Haus und Netz (bei zwei Anlagen jede mit ihrem Speicher), Gesamt-Ladestand in kWh und eine Karte für dein Dashboard.
- **Feste Entitäten (MQTT):** Sensoren, Energiezähler für das Energie-Dashboard und Schalter für Regelung, Testmodus und Not-Aus.
- **Auswertung:** Tagesstatistik mit Autarkie, Ersparnis und der Energie aus den Speichern sowie ein „Was wäre wenn“-Replay mit deinen echten Verlaufsdaten.
- **Sicherheit:** Testmodus, Not-Aus-Knopf, automatischer Rückfall auf den eigenen Modus des Herstellers (z. B. Eigenverbrauch), ein Wächter, der bei einem
  Ausfall eingreift, Benachrichtigungen aufs Handy und ein Selbsttest, der deine Einrichtung prüft.

## Voraussetzungen

- **Home Assistant OS oder Supervised** (du hast einen Add-on-Store). Home Assistant Container und Core unterstützen keine Add-ons.
- Ein **Speicher mit Home-Assistant-Anbindung**, bei Anker die offizielle Integration [Anker Solix Official](https://github.com/anker-charging/ha-anker-solix-official).
- Ein **Sensor für die Netzleistung in Watt**, z. B. ein Lesekopf am Stromzähler oder ein Shelly EM (positiv = Bezug, negativ = Einspeisung).
- Empfohlen: ein **Sensor für die Solarleistung** je Speicher.

## Installation

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store → ⋮ (oben rechts) → Repositories** und diese Adresse hinzufügen:
   `https://github.com/DEIN-NAME/solasi` (oder den Knopf oben benutzen).
2. **SOLASI** öffnen, **Installieren** und **Starten**, dann **In der Seitenleiste anzeigen** einschalten.
3. SOLASI in der Seitenleiste öffnen. Die Willkommensseite führt durch die Einrichtung.

## Erste Schritte

1. **Zähler und Speicher auswählen** (*Einrichtung*). Der Selbsttest unter *System* zeigt, ob alles passt.
2. **Testmodus eingeschaltet lassen** und **Regelung** einschalten. SOLASI rechnet dann alles durch, sendet aber nichts. Im *Protokoll* siehst du, was passieren würde.
3. Wenn die Werte plausibel sind, den **Testmodus ausschalten**. Ab jetzt steuert SOLASI deinen Speicher.
4. Mach dich vorher mit dem **Not-Aus** vertraut: Ein Klick stoppt SOLASI und gibt den Speicher an seinen eigenen Modus zurück.

Die ausführliche Anleitung steht in der [Dokumentation](solasi/DOCS.md), die du auch im Add-on unter **Dokumentation** findest.

## Unterstützte Speicher

| Speicher | Anbindung | Stand |
|---|---|---|
| Anker SOLIX Solarbank 4 E5000 Pro (auch zwei) | Anker Solix Official | im Alltag getestet |
| Marstek (z. B. Venus), Speicher mit einer Leistungszahl mit Vorzeichen oder mit Modus und Leistungen | passende Home-Assistant-Integration | nach Herstellerbeschreibung umgesetzt, bisher nur in Simulationen getestet |
| Wechselrichter mit Leistungsbegrenzung (z. B. über OpenDTU) | Zahl für die Abgabe | wie oben |
| Alle anderen (z. B. Victron, Huawei, Sungrow) | eigenes Skript | wie oben |

Bei allem außer Anker bitte **zuerst im Testmodus beobachten** und gern eine Rückmeldung geben.

## Häufige Fragen

**Mein Speicher liefert nichts mehr, obwohl der Ladestand noch über 0 % liegt.**
Die meisten Speicher haben eine eigene Entladegrenze (bei Anker in der App einstellbar), unter der sie nichts mehr abgeben. SOLASI kann diese Grenze nicht überschreiben.
Trage unter *Einrichtung* die Entität „Entladegrenze“ deines Speichers ein, dann richtet sich SOLASI automatisch danach. Merkt SOLASI, dass ein Speicher trotz Anforderung nichts abgibt,
zeigt es „Grenze“ an und fragt ihn eine Weile nicht mehr an, bis sich sein Ladestand ändert.

**Warum steht in der Überschrift „Das Netz versorgt dein Haus“, obwohl SOLASI Entladen anfordert?**
Die Überschrift zeigt, was wirklich fließt, nicht was SOLASI anfordert. Liefert der Speicher gerade nichts (zum Beispiel an seiner Entladegrenze), siehst du das sofort.

**Was passiert bei vollem Speicher?**
Je nach Gerät reicht der Speicher den Solarstrom nur durch und folgt Vorgaben der Software nicht. Ob dann trotzdem eingespeist wird, zeigt dir der Selbsttest unter *System*
(„Abregelung bei vollem Speicher“).

**Wie bekomme ich das Menü auf dem Handy?**
Die Leiste mit Übersicht, Speicher, Statistik, Überschuss und „Mehr“ steht oben. Unter „Mehr“ findest du alles Weitere.

**Wie stoppe ich SOLASI sofort?**
Mit dem **Not-Aus** oben rechts. Der Speicher geht dann zurück in seinen eigenen Modus. „Fortsetzen“ übergibt die Regelung wieder an SOLASI.

## Wichtige Hinweise

- **Teste immer zuerst im Testmodus.** SOLASI steuert echte Hardware.
- **Beachte die Einspeisegrenzen** deiner Anlage (z. B. 800 VA bei Steckersolargeräten) und die Vorgaben deines Netzbetreibers. Die Voreinstellung für die Gesamtabgabe ist bewusst vorsichtig.
- **Nutzung auf eigene Verantwortung.** Die Software wird ohne Gewähr bereitgestellt (siehe [Lizenz](LICENSE)).
- **Datenschutz:** SOLASI spricht nur mit deinem Home Assistant. Es werden keine Daten an Dritte gesendet.

## Hilfe und Rückmeldung

- Öffne unter **System → Selbsttest** die Systemprüfung, sie nennt Fehler in der Einrichtung mit Lösungsvorschlag.
- Das **Protokoll** unter *System* zeigt, was SOLASI getan hat.
- Findest du einen Fehler oder hast du eine Idee, [melde dich hier](https://github.com/DEIN-NAME/solasi/issues/new/choose). Bitte hänge Selbsttest und Protokoll an, aber keine Zugangsdaten.

## Über das Projekt

**SOLASI** steht für **SOL**ar-**A**nlagen-**S**peicher-**I**nterface. Das Projekt ist unabhängig und nicht mit *SolarAssistant*, Anker oder anderen Herstellern verbunden.
Die Regelstrategie orientiert sich am Forum-Blueprint „Anker SOLIX 4 Pro – Lokale Nulleinspeisung & Eco-Modus“ von MBP996 im Home-Assistant-Forum, der Code ist eine eigene Umsetzung.
Freie Software unter der [MIT-Lizenz](LICENSE).
