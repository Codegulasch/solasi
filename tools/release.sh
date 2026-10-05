#!/usr/bin/env bash
# Veröffentlicht eine neue Version: Tests, Version setzen, committen, Tag anlegen.
# Aufruf:  tools/release.sh 1.7.0 [--all] [--push] [--skip-tests]
#   --all   committet vorhandene Änderungen (z. B. nach tools/sync_from_zip.sh) vorher als „Update auf x.y.z“
#   --push  lädt Commit und Tag danach hoch
#   --skip-tests  überspringt die lokalen Tests (GitHub führt sie nach dem Hochladen aus, siehe Reiter „Actions“)
set -euo pipefail
cd "$(dirname "$0")/.."
# sed -i unterscheidet sich zwischen Linux (GNU) und macOS (BSD): bei macOS braucht es ein leeres Suffix.
sedi() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }
ver="${1:-}"; shift || true
push=""; all=""; skip=""
for a in "$@"; do case "$a" in --push) push=1;; --all) all=1;; --skip-tests) skip=1;; *) echo "Unbekannte Option: $a"; exit 1;; esac; done
tests_possible() { python3 -c "import aiohttp, pytest, pytest_asyncio, jinja2" >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; }
[[ "$ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Aufruf: tools/release.sh x.y.z [--all] [--push] [--skip-tests]"; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "Dieser Ordner ist kein Git-Repository (es fehlt das versteckte .git)."
  echo "Hole dir eine Arbeitskopie von GitHub, zum Beispiel:   gh repo clone DEIN-NAME/solasi solasi-git"
  exit 1
}
if [ -n "$(git status --porcelain)" ]; then
  if [ -n "$all" ]; then
    git add -A && git commit -q -m "Update auf ${ver}" && echo "Änderungen als „Update auf ${ver}“ committet."
  else
    echo "Es gibt uncommittete Änderungen. Bitte erst committen oder --all verwenden."; git status --short; exit 1
  fi
fi
grep -q "^## ${ver}$" solasi/CHANGELOG.md || { echo "In solasi/CHANGELOG.md fehlt der Abschnitt '## ${ver}'."; exit 1; }
git rev-parse "v${ver}" >/dev/null 2>&1 && { echo "Tag v${ver} gibt es schon."; exit 1; }
old=$(grep '^version:' solasi/config.yaml | sed -E 's/version:[[:space:]]*"?([^"]*)"?/\1/')
[ "$old" != "$ver" ] || echo "Hinweis: config.yaml hat bereits Version ${ver}."
if [ -n "$skip" ]; then
  echo "Lokale Tests übersprungen. GitHub führt sie nach dem Hochladen aus (Reiter „Actions“)."
elif tests_possible; then
  tools/test_all.sh
else
  echo "Lokale Tests sind hier nicht möglich (es fehlen Python-Pakete oder Node.js)."
  echo "Mit  --skip-tests  überspringen: GitHub führt sie nach dem Hochladen aus (Reiter „Actions“)."
  exit 1
fi
sedi -E "s/^version:.*/version: \"${ver}\"/" solasi/config.yaml
git add solasi/config.yaml
git commit -m "Release ${ver}" --allow-empty
git tag -a "v${ver}" -m "SOLASI ${ver}"
echo "Fertig: Version ${ver} committet und getaggt."
if [ -n "$push" ]; then
  git push && git push --tags
  echo "Hochgeladen. GitHub Actions legt das Release an."
else
  echo "Zum Hochladen:  git push && git push --tags"
fi
