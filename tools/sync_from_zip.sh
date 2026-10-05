#!/usr/bin/env bash
# Spielt ein neues Paket (solasi_repo.zip) in dieses Repository ein.
# Ersetzt: solasi/, .github/, tools/, README.md und DEVELOPMENT.md. Nicht angefasst werden repository.yaml und LICENSE.
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
for f in repository.yaml LICENSE .gitignore .gitattributes; do
  [ -f "$f" ] || { [ -f "$src/$f" ] && cp "$src/$f" "$f" && echo "Neu angelegt: $f"; }
done
# README.md und DEVELOPMENT.md gehören zum Paket und werden aktualisiert. Konto und Repository-Name kommen aus repository.yaml.
ref="$(grep -m1 '^url:' repository.yaml 2>/dev/null | sed -E 's#.*github\.com/([^/ "]+)/([^/ "]+).*#\1/\2#' || true)"
owner="${ref%%/*}"; rname="${ref#*/}"
for f in README.md DEVELOPMENT.md; do
  [ -f "$src/$f" ] || continue
  cp "$src/$f" "$f"
  if [ -n "$ref" ] && [ "$owner" != "$ref" ]; then
    sedi "s#github.com/DEIN-NAME/[A-Za-z0-9._-]*#github.com/${owner}/${rname}#g; s#github.com%2FDEIN-NAME%2F[A-Za-z0-9._-]*#github.com%2F${owner}%2F${rname}#g; s#DEIN-NAME#${owner}#g" "$f"
  fi
done
chmod +x tools/*.sh
echo; echo "Eingespielt."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Änderungen:"; git status --short
else
  echo "ACHTUNG: Dieser Ordner ist kein Git-Repository (es fehlt das versteckte .git), hochladen geht so nicht."
  echo "Hole dir eine Arbeitskopie:   gh repo clone DEIN-NAME/solasi solasi-git   und führe das Einspielen dort aus."
fi
ver="$(grep -m1 '^version:' solasi/config.yaml | sed -E 's/version:[[:space:]]*"?([^"]*)"?/\1/')"
echo; echo "Nächste Schritte: mit  git diff  prüfen, dann veröffentlichen:"
echo "  bash tools/release.sh ${ver} --all --push"
