#!/usr/bin/env bash
# Spielt ein neues Paket (solasi_repo.zip) in dieses Repository ein.
# Ersetzt nur: solasi/, .github/, tools/. Nicht angefasst werden repository.yaml, LICENSE und README.md.
# Aufruf:  tools/sync_from_zip.sh ~/Downloads/solasi_repo.zip
set -euo pipefail
# sed -i unterscheidet sich zwischen Linux (GNU) und macOS (BSD): bei macOS braucht es ein leeres Suffix.
sedi() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }
zip="${1:-}"
[ -f "$zip" ] || { echo "Aufruf: tools/sync_from_zip.sh <paket.zip>"; exit 1; }
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
unzip -q "$zip" -d "$tmp"
src="$tmp"; [ -d "$src/solasi-repo" ] && src="$src/solasi-repo"
[ -d "$src/solasi" ] || { echo "Das Paket enthält keinen Ordner solasi."; exit 1; }
copy_dir() {   # $1 = Ordnername
  [ -d "$src/$1" ] || return 0
  if command -v rsync >/dev/null; then
    rsync -a --delete --exclude node_modules --exclude __pycache__ "$src/$1/" "$1/"
  else
    rm -rf "$1" && cp -a "$src/$1" "$1"
  fi
}
old_url="$(grep -m1 '^url:' solasi/config.yaml 2>/dev/null || true)"   # deine Projekt-URL soll erhalten bleiben
copy_dir solasi
[ -n "$old_url" ] && sedi "s#^url:.*#${old_url}#" solasi/config.yaml
copy_dir .github
copy_dir tools
for f in repository.yaml LICENSE README.md .gitignore; do
  [ -f "$f" ] || { [ -f "$src/$f" ] && cp "$src/$f" "$f" && echo "Neu angelegt: $f"; }
done
chmod +x tools/*.sh
echo; echo "Eingespielt. Änderungen:"; git status --short || true
ver="$(grep -m1 '^version:' solasi/config.yaml | sed -E 's/version:[[:space:]]*"?([^"]*)"?/\1/')"
echo; echo "Nächste Schritte: mit  git diff  prüfen, dann veröffentlichen:"
echo "  tools/release.sh ${ver} --all --push"
