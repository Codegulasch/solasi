#!/usr/bin/env bash
# Erster Upload nach GitHub: ersetzt die Platzhalter, committet und lädt alles hoch.
#
# Aufruf:  tools/first_push.sh <github-name> [repo-name] [--public] [--release]
#   github-name  dein GitHub-Benutzername (Standard: der mit "gh auth login" angemeldete) oder deine Organisation
#   repo-name    Name des Repositorys (Standard: solasi)
#   --public     Repository öffentlich anlegen (Standard: privat, nur mit GitHub CLI "gh")
#   --release    zusätzlich den Tag v<Version> anlegen und hochladen (löst das Release auf GitHub aus)
#
# Zwei Wege:
#   * Mit GitHub CLI (gh auth login): Das Repository wird automatisch angelegt.
#   * Ohne gh: Lege auf github.com ein LEERES Repository an (ohne README, ohne Lizenz) und führe dann dieses Skript aus.
set -euo pipefail
cd "$(dirname "$0")/.."

# sed -i unterscheidet sich zwischen Linux (GNU) und macOS (BSD): bei macOS braucht es ein leeres Suffix.
sedi() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }

user=""; repo="solasi"; visibility="--private"; release=""
for a in "$@"; do
  case "$a" in
    --public) visibility="--public" ;;
    --release) release=1 ;;
    -*) echo "Unbekannte Option: $a"; exit 1 ;;
    *) if [ -z "$user" ]; then user="$a"; else repo="$a"; fi ;;
  esac
done

# Wer ist bei der GitHub CLI angemeldet? Das ist der Standard für den Namen.
gh_login=""
if [ -z "${SOLASI_REMOTE_URL:-}" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  gh_login="$(gh api user -q .login 2>/dev/null || true)"
fi
if [ -z "$user" ] && [ -n "$gh_login" ]; then
  user="$gh_login"; echo "Verwende deinen GitHub-Namen: $user"
fi
[ -n "$user" ] || { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
if [ -n "$gh_login" ] && [ "$(echo "$user" | tr 'A-Z' 'a-z')" != "$(echo "$gh_login" | tr 'A-Z' 'a-z')" ]; then
  echo "Achtung: Du bist bei GitHub als „${gh_login}“ angemeldet, gibst aber „${user}“ als Konto an."
  echo "Der zweite Teil (Repository-Name) kommt NACH dem Konto:  tools/first_push.sh ${gh_login} ${repo}"
  if [ -t 0 ]; then
    read -r -p "Trotzdem unter „${user}“ anlegen (nur sinnvoll für eine Organisation)? [j/N] " yn
    case "$yn" in j|J|y|Y) ;; *) echo "Abgebrochen."; exit 1 ;; esac
  else
    echo "Abgebrochen."; exit 1
  fi
fi
[[ "$user" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$ ]] || { echo "Ungültiger GitHub-Name: $user"; exit 1; }
[[ "$repo" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Ungültiger Repository-Name: $repo"; exit 1; }
command -v git >/dev/null || { echo "git ist nicht installiert."; exit 1; }
if [ -z "$(git config user.email || true)" ] || [ -z "$(git config user.name || true)" ]; then
  echo "Git kennt deinen Namen noch nicht. Bitte einmalig einrichten und das Skript neu starten:"
  echo '  git config --global user.name  "Dein Name"'
  echo '  git config --global user.email "deine@mail.de"'
  exit 1
fi

addon="$(ls -d */ | grep -v -e tools -e .github | head -1 | tr -d '/')"
version="$(grep -m1 '^version:' "$addon/config.yaml" | sed -E 's/version:[[:space:]]*"?([^"]*)"?/\1/')"
url="${SOLASI_REMOTE_URL:-https://github.com/${user}/${repo}.git}"
pages="https://github.com/${user}/${repo}"

echo "Repository:  ${pages}"
echo "Add-on:      ${addon} (Version ${version})"

# 1) Platzhalter bzw. früher eingesetzte Werte ersetzen (das Skript ist wiederholbar)
old_ref="$(grep -m1 '^url:' repository.yaml 2>/dev/null | sed -E 's#.*github\.com/([^/ "]+)/([^/ "]+).*#\1/\2#' || true)"
old_owner="${old_ref%%/*}"; old_repo="${old_ref#*/}"
[ -n "$old_ref" ] && [ "$old_owner" != "$old_ref" ] || { old_owner="DEIN-NAME"; old_repo="solasi"; }
for f in repository.yaml README.md DEVELOPMENT.md "$addon/config.yaml"; do
  [ -f "$f" ] || continue
  sedi "s#github.com/${old_owner}/${old_repo}#github.com/${user}/${repo}#g; s#github.com%2F${old_owner}%2F${old_repo}#github.com%2F${user}%2F${repo}#g; s#DEIN-NAME#${user}#g" "$f"
done
sedi "s#^maintainer:.*#maintainer: ${user}#" repository.yaml
if grep -rq "DEIN-NAME" repository.yaml README.md DEVELOPMENT.md "$addon/config.yaml" 2>/dev/null; then
  echo "Es stehen noch Platzhalter (DEIN-NAME) in den Dateien."; exit 1
fi
echo "Konto und Repository-Name eingetragen: ${user}/${repo}"

# 2) Git vorbereiten und committen
[ -d .git ] || git init -q -b main
git checkout -q -B main 2>/dev/null || true
git add -A
if git diff --cached --quiet; then
  echo "Nichts Neues zu committen."
else
  git commit -q -m "SOLASI ${version}"
  echo "Commit angelegt."
fi

# 3) Hochladen
if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin ist schon gesetzt: $(git remote get-url origin)"
  git push -u origin main
elif [ -z "${SOLASI_REMOTE_URL:-}" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  echo "Lege das Repository mit der GitHub CLI an (${visibility#--}) …"
  gh repo create "${user}/${repo}" "$visibility" --source . --remote origin --push
else
  git remote add origin "$url"
  echo "Lade hoch nach ${url} …"
  git push -u origin main
fi

# 4) Optional: Release
if [ -n "$release" ]; then
  if git rev-parse "v${version}" >/dev/null 2>&1; then
    echo "Tag v${version} gibt es schon."
  else
    git tag -a "v${version}" -m "SOLASI ${version}"
  fi
  git push origin "v${version}"
  echo "Tag v${version} hochgeladen. GitHub Actions legt das Release an."
fi

echo
echo "Fertig. Dein Repository: ${pages}"
echo "In Home Assistant: Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories → ${pages}"
echo "Danach in GitHub unter Actions prüfen, ob die Tests grün sind."
