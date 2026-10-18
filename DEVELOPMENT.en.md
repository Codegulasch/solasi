# Development

🇩🇪 [Deutsche Version](DEVELOPMENT.md)

This document is for anyone who contributes to SOLASI or publishes it themselves. The guide for users is in the [README](README.en.md) and in the
[documentation](solasi/DOCS.en.md).

## Structure

| Path | Contents |
|---|---|
| `solasi/config.yaml` | Add-on description and **version** |
| `tools/flow_shared.js` | Energy flow, history and heading for the interface and the card. After changes, run `python tools/sync_flow.py`; a test checks that both copies are identical |
| `solasi/app/` | Control logic in Python (`controller.py`, `drivers.py`, `energy.py`, `watchdog.py`, `replay.py`, `mqtt.py` for the MQTT entities …), web interface in `static/`, dashboard card in `card/` |
| `solasi/tests/` | Python tests against a simulated Home Assistant, interface tests in `tests/ui` (jsdom) |
| `solasi/CHANGELOG.md` | Changes for users (shown in Home Assistant and in the GitHub release) |
| `solasi/DOCS.md`, `solasi/README.md` | Guide and short description for users |
| `.github/workflows/` | CI (tests, Docker build, configuration check) and release |
| `tools/` | Helper scripts (see below) |

## Tests

```bash
# Python tests (control, drivers, watchdog, replay, web API)
pip install aiohttp==3.10.5 pytest pytest-asyncio pyyaml jinja2
cd solasi && python -m pytest -q

# Interface tests (jsdom, needs Node.js)
cd solasi/tests/ui && npm install && npm test

# everything together
tools/test_all.sh
```

CI runs the same tests and additionally builds the Docker image.

## First upload to GitHub

1. Either create an **empty** repository on github.com (no README, no license) or install the [GitHub CLI](https://cli.github.com) and sign in with `gh auth login`.
2. In the unpacked folder:

```bash
tools/first_push.sh                                                # with gh: signed-in name, private repository
tools/first_push.sh <account>                                      # without gh: into the empty repository created beforehand
tools/first_push.sh <account> solasi --public --release            # public and straight away as a release
```

The script enters the account and repository name (also on a second run), commits, uploads and, if requested, creates the release tag. The account comes first,
the repository name after it. Without `gh`, Git asks for a username and a personal access token.

**macOS:** Open Terminal, install the command line tools on the first `git`, set name and email with `git config --global user.name "…"` and
`git config --global user.email "…"`, and install the GitHub CLI with `brew install gh`. It is best to start scripts with `bash tools/…`.

## Publishing a new version

1. Make changes and run the tests (`tools/test_all.sh`).
2. At the top of `solasi/CHANGELOG.md`, add a section `## x.y.z`. It appears for users and in the release, so please write it in user language.
3. Run `tools/release.sh x.y.z --push`. The script checks the state, starts the tests, sets the version in `config.yaml`, commits, creates the tag `vx.y.z` and uploads.
   Without local Python and Node tools, use `--skip-tests` (GitHub runs the tests after the upload).
4. GitHub Actions creates the release from the tag, and Home Assistant then offers the update.

**Important:** Without a higher version in `solasi/config.yaml`, users do not see an update. CI checks this on pull requests.

## Applying a new package (zip)

This requires a **Git working copy** (a folder with a hidden `.git`). A freshly unpacked zip folder is not one. Get one with `gh repo clone <account>/solasi solasi-git`.

```bash
cd ~/solasi-git
ZIP="$(ls -t ~/Downloads/solasi_repo*.zip | head -1)"                # newest zip
unzip -p "$ZIP" solasi-repo/solasi/config.yaml | grep '^version'     # check version
bash tools/sync_from_zip.sh "$ZIP"                                   # applies add-on, documentation, CI and scripts
git diff --stat                                                      # see what has changed
bash tools/release.sh x.y.z --all --skip-tests --push                # use the version from the package
```

Applying replaces `solasi/`, `.github/`, `tools/`, `README.md` and `DEVELOPMENT.md`, **not** `repository.yaml` and `LICENSE`. Account and repository name are taken from
`repository.yaml`, and the project URL in `config.yaml` is kept. Removed files also disappear from the repository.

### Windows (PowerShell)

On Windows you do not need Bash. Run `winget install --id Git.Git -e` and `winget install --id GitHub.cli -e` once, reopen PowerShell, run `gh auth login` and
set `git config --global user.name`/`user.email`.

```powershell
gh repo clone <account>/solasi $HOME\solasi-git
$zip = (Get-ChildItem "$HOME\Downloads\solasi_repo*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
Expand-Archive -Path $zip -DestinationPath "$env:TEMP\solasi-neu" -Force
powershell -ExecutionPolicy Bypass -File "$env:TEMP\solasi-neu\solasi-repo\tools\sync_from_zip.ps1" -Source "$env:TEMP\solasi-neu" -Repo "$HOME\solasi-git"
cd $HOME\solasi-git
powershell -ExecutionPolicy Bypass -File tools\release.ps1 -All -Push
```

`release.ps1` takes the version from `config.yaml` and skips local tests.

## Renaming the project

`tools/rename.py "New Name"` replaces name, identifier, entities, card name and texts, renames folders and files, and regenerates the logo. The identifier changes in the process:
for Home Assistant this is a new add-on, and dashboards must be adjusted to `custom:<identifier>-card` and `sensor.<identifier>`. Export the settings beforehand.
