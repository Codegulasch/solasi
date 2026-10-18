# Entwicklung

🇬🇧 [English version](DEVELOPMENT.en.md)

Dieses Dokument richtet sich an alle, die an SOLASI mitarbeiten oder es selbst veröffentlichen. Die Anleitung für Nutzer steht in der [README](README.md) und in der
[Dokumentation](solasi/DOCS.md).

## Aufbau

| Pfad | Inhalt |
|---|---|
| `solasi/config.yaml` | Add-on-Beschreibung und **Version** |
| `tools/flow_shared.js` | Energiefluss, Verlauf und Überschrift für Oberfläche und Karte. Nach Änderungen `python tools/sync_flow.py` ausführen; ein Test prüft, dass beide Kopien gleich sind |
| `solasi/app/` | Regelung in Python (`controller.py`, `drivers.py`, `energy.py`, `watchdog.py`, `replay.py`, `mqtt.py` für die MQTT-Entitäten …), Weboberfläche in `static/`, Dashboard-Karte in `card/` |
| `solasi/tests/` | Python-Tests gegen einen simulierten Home Assistant, Oberflächen-Tests in `tests/ui` (jsdom) |
| `solasi/CHANGELOG.md` | Änderungen für Nutzer (wird in Home Assistant und im GitHub-Release angezeigt) |
| `solasi/DOCS.md`, `solasi/README.md` | Anleitung und Kurzbeschreibung für Nutzer |
| `.github/workflows/` | CI (Tests, Docker-Build, Konfigurationsprüfung) und Release |
| `tools/` | Hilfsskripte (siehe unten) |

## Tests

```bash
# Python-Tests (Regelung, Treiber, Wächter, Replay, Web-API)
pip install aiohttp==3.10.5 pytest pytest-asyncio pyyaml jinja2
cd solasi && python -m pytest -q

# Oberflächen-Tests (jsdom, braucht Node.js)
cd solasi/tests/ui && npm install && npm test

# alles zusammen
tools/test_all.sh
```

Die CI führt dieselben Tests aus und baut zusätzlich das Docker-Image.

## Erster Upload nach GitHub

1. Entweder auf github.com ein **leeres** Repository anlegen (ohne README, ohne Lizenz) oder die [GitHub CLI](https://cli.github.com) installieren und mit `gh auth login` anmelden.
2. Im entpackten Ordner:

```bash
tools/first_push.sh                                                # mit gh: angemeldeter Name, privates Repository
tools/first_push.sh <konto>                                        # ohne gh: in das vorher angelegte leere Repository
tools/first_push.sh <konto> solasi --public --release              # öffentlich und gleich als Release
```

Das Skript trägt Konto und Repository-Name ein (auch bei einem zweiten Lauf), committet, lädt hoch und legt auf Wunsch den Release-Tag an. Das Konto kommt zuerst,
der Repository-Name danach. Ohne `gh` fragt Git nach Benutzername und einem Personal Access Token.

**macOS:** Terminal öffnen, beim ersten `git` die Kommandozeilen-Werkzeuge installieren, Namen und Mail mit `git config --global user.name "…"` und
`git config --global user.email "…"` setzen, die GitHub CLI mit `brew install gh`. Skripte am besten mit `bash tools/…` starten.

## Neue Version veröffentlichen

1. Änderungen machen und Tests laufen lassen (`tools/test_all.sh`).
2. In `solasi/CHANGELOG.md` oben einen Abschnitt `## x.y.z` ergänzen. Er erscheint für Nutzer und im Release, bitte in Nutzersprache.
3. `tools/release.sh x.y.z --push` ausführen. Das Skript prüft den Stand, startet die Tests, setzt die Version in `config.yaml`, committet, legt den Tag `vx.y.z` an und lädt hoch.
   Ohne lokale Python- und Node-Werkzeuge mit `--skip-tests` (GitHub führt die Tests nach dem Hochladen aus).
4. GitHub Actions legt aus dem Tag das Release an, Home Assistant bietet danach das Update an.

**Wichtig:** Ohne höhere Version in `solasi/config.yaml` sehen Nutzer kein Update. Die CI prüft das bei Pull Requests.

## Neuen Paketstand (Zip) einspielen

Voraussetzung ist eine **Git-Arbeitskopie** (ein Ordner mit verstecktem `.git`). Ein frisch entpackter Zip-Ordner ist keine. Hol dir eine mit `gh repo clone <konto>/solasi solasi-git`.

```bash
cd ~/solasi-git
ZIP="$(ls -t ~/Downloads/solasi_repo*.zip | head -1)"                # neueste Zip
unzip -p "$ZIP" solasi-repo/solasi/config.yaml | grep '^version'     # Version prüfen
bash tools/sync_from_zip.sh "$ZIP"                                   # spielt Add-on, Dokumentation, CI und Skripte ein
git diff --stat                                                      # ansehen, was sich geändert hat
bash tools/release.sh x.y.z --all --skip-tests --push                # Version aus dem Paket verwenden
```

Das Einspielen ersetzt `solasi/`, `.github/`, `tools/`, `README.md` und `DEVELOPMENT.md`, **nicht** `repository.yaml` und `LICENSE`. Konto und Repository-Name werden aus
`repository.yaml` übernommen, die Projekt-URL in `config.yaml` bleibt erhalten. Entfernte Dateien verschwinden auch im Repository.

### Windows (PowerShell)

Unter Windows brauchst du kein Bash. Einmalig `winget install --id Git.Git -e` und `winget install --id GitHub.cli -e`, PowerShell neu öffnen, `gh auth login` und
`git config --global user.name`/`user.email` setzen.

```powershell
gh repo clone <konto>/solasi $HOME\solasi-git
$zip = (Get-ChildItem "$HOME\Downloads\solasi_repo*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
Expand-Archive -Path $zip -DestinationPath "$env:TEMP\solasi-neu" -Force
powershell -ExecutionPolicy Bypass -File "$env:TEMP\solasi-neu\solasi-repo\tools\sync_from_zip.ps1" -Source "$env:TEMP\solasi-neu" -Repo "$HOME\solasi-git"
cd $HOME\solasi-git
powershell -ExecutionPolicy Bypass -File tools\release.ps1 -All -Push
```

`release.ps1` nimmt die Version aus `config.yaml` und überspringt lokale Tests.

## Projekt umbenennen

`tools/rename.py "Neuer Name"` ersetzt Name, Kennung, Entitäten, Kartenname und Texte, benennt Ordner und Dateien um und erzeugt das Logo neu. Die Kennung ändert sich dabei:
Für Home Assistant ist das ein neues Add-on, Dashboards müssen auf `custom:<kennung>-card` und `sensor.<kennung>` angepasst werden. Vorher die Einstellungen exportieren.
