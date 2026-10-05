# SOLASI – Add-on für Home Assistant

Nulleinspeisung für **Anker SOLIX 4 E5000 Pro** und andere Heimspeicher (Marstek, Wechselrichter-Limit, eigenes Skript) mit
Live-Oberfläche, Eco-Modus, Überschusssteuerung (Wallbox, Heizstab), Kill-Switch mit Rückfall auf den eigenen Modus des
Speichers, Selbsttest, Benachrichtigungen, Statistik und Replay. Dazu eine Dashboard-Karte mit Energiefluss.

**SOLASI** steht für **SOL**ar-**A**nlagen-**S**peicher-**I**nterface. Das Projekt ist unabhängig und steht in keiner Verbindung zu
*SolarAssistant* (solar-assistant.io) oder zu Anker.

> **Sicherheitshinweis:** SOLASI steuert Hardware. Fang immer im **Testmodus** an und prüfe im Protokoll, was gesendet würde.
> Die Software wird ohne Gewähr bereitgestellt (siehe Lizenz). Speichertypen außer Anker sind nach der Dokumentation der
> jeweiligen Integrationen umgesetzt und im Simulator getestet, aber nicht an jeder Hardware.

## Installation

1. In Home Assistant: *Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories* und diese Adresse hinzufügen:
   `https://github.com/Codegulasch/solasi`
   (oder per Knopf: [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FCodegulasch%2Fsolasi))
2. **SOLASI** installieren, starten und „In der Seitenleiste anzeigen“ aktivieren.
3. Die Einrichtung steht in der [Dokumentation](solasi/DOCS.md), die auch im Reiter „Dokumentation“ des Add-ons erscheint.

Updates erscheinen automatisch im Add-on-Store, sobald eine neue Version veröffentlicht ist.

## Auf GitHub veröffentlichen (einmalig)

1. Entweder auf github.com ein **leeres** Repository anlegen (z. B. `solasi`, ohne README und ohne Lizenz) oder die
   [GitHub CLI](https://cli.github.com) installieren und mit `gh auth login` anmelden (dann legt das Skript das Repository selbst an).
2. Im entpackten Ordner:

```bash
tools/first_push.sh                                 # mit gh: nimmt den angemeldeten GitHub-Namen, legt ein privates Repository an
tools/first_push.sh <dein-github-name>             # ohne gh: in das vorher angelegte leere Repository
tools/first_push.sh <dein-github-name> solasi --public --release   # öffentlich und gleich als Release 1.0.x
```

Das Skript trägt Konto und Repository-Name ein (auch bei einem zweiten Lauf), committet, lädt hoch und legt auf Wunsch den Release-Tag an.
Das Konto kommt zuerst, der Repository-Name danach: `tools/first_push.sh <konto> <repository>`.
Ohne `gh` fragt Git beim Hochladen nach Benutzername und einem **Personal Access Token** (kein Passwort); alternativ per SSH.
Danach unter *Actions* prüfen, ob die Tests grün sind.

**macOS:** Terminal öffnen (`Cmd+Leertaste`, „Terminal“), `cd ~/Downloads/solasi-repo`, beim ersten `git` die angebotenen
Kommandozeilen-Werkzeuge installieren, Namen und Mail einmalig mit `git config --global user.name "…"` und
`git config --global user.email "…"` setzen. Die GitHub CLI gibt es mit `brew install gh` (Homebrew, brew.sh) oder als Installer auf cli.github.com.
Starte die Skripte am besten mit `bash tools/first_push.sh …`.

## Entwicklung

```bash
# Python-Tests (Regelung, Treiber, Wächter, Replay, Web-API gegen einen simulierten Home Assistant)
pip install aiohttp pytest pytest-asyncio
cd solasi && python -m pytest -q

# Oberflächen-Tests (jsdom)
cd solasi/tests/ui && npm install && npm test

# oder alles zusammen
tools/test_all.sh
```

Aufbau: `solasi/app` (Regelung in Python, Weboberfläche in `static/`, Dashboard-Karte in `card/`),
`solasi/tests` (Tests), `solasi/config.yaml` (Add-on-Beschreibung und **Version**).

### Neue Version veröffentlichen

1. Änderungen machen, Tests laufen lassen (`tools/test_all.sh`).
2. In `solasi/CHANGELOG.md` oben einen Abschnitt `## x.y.z` mit den Änderungen ergänzen.
3. `tools/release.sh x.y.z --push` ausführen. Das Skript prüft den Stand, startet die Tests, setzt die Version in
   `config.yaml`, committet, legt den Tag `vx.y.z` an und lädt beides hoch (ohne `--push` nur lokal, dann `git push && git push --tags`).
4. GitHub Actions legt aus dem Tag das Release an, Home Assistant bietet danach das Update an.

**Wichtig:** Ohne höhere Version in `solasi/config.yaml` sehen die Nutzer kein Update. Die CI prüft das bei Pull Requests.

### Neuen Paketstand (Zip) einspielen

Liegt eine neue Fassung als Zip vor:

```bash
tools/sync_from_zip.sh ~/Downloads/solasi_repo.zip    # spielt Add-on, CI und Skripte ein
git diff                                              # ansehen, was sich geändert hat
tools/release.sh 1.1.0 --all --push                   # Version aus dem Paket verwenden (das Skript nennt sie)
```

Das Einspielen ersetzt nur `solasi/`, `.github/` und `tools/`, **nicht** `repository.yaml`, `LICENSE` und dein `README.md`;
deine Projekt-URL in `config.yaml` bleibt erhalten. Entfernte Dateien verschwinden auch im Repository.

### Projekt umbenennen

`tools/rename.py "Neuer Name"` ersetzt Name, Kennung, Entitäten, Kartenname und Texte, benennt Ordner und Dateien um und erzeugt das Logo
neu. Die Kennung ändert sich dabei: Für Home Assistant ist das ein neues Add-on, Dashboards müssen auf `custom:<kennung>-card` und
`sensor.<kennung>` angepasst werden. Vorher die Einstellungen exportieren.

## Danksagung

Die Regelstrategie (Netzbilanz, Ein-/Ausschalt-Schwellen, Offsets, Eco-Modus, Modus-Wächter) orientiert sich am
Forum-Blueprint „Anker SOLIX 4 Pro – Lokale Nulleinspeisung & Eco-Modus“ von MBP996 im Home-Assistant-Forum. Der Code in
diesem Repository ist eine eigene Neuimplementierung in Python mit eigener Architektur und Erweiterungen. **Vor einer
öffentlichen Veröffentlichung bitte die Lizenz des Blueprints prüfen bzw. den Autor um Einverständnis bitten.**
