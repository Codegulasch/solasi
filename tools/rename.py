#!/usr/bin/env python3
"""Benennt das Projekt um (Anzeigename, Kennung, Entitäten, Karte, Texte, Ordner) und erzeugt das Logo neu.

Aufruf:
    tools/rename.py "Neuer Name" [--slug neuer_name] [--dry-run]

Was passiert:
  * Anzeigename, Kennung (slug) des Add-ons, Entitäts-Präfix (sensor.<slug>…), Kartenname (<slug>-card) und alle Texte werden ersetzt.
  * Der Add-on-Ordner und Dateien mit dem alten Namen werden umbenannt.
  * logo.png wird neu erzeugt, wenn Pillow installiert ist.
Nicht angefasst werden CHANGELOG.md (Verlauf) und dieses Skript.
Die Kennung ändert sich: Für Home Assistant ist das ein neues Add-on. Vorher die Einstellungen exportieren, danach importieren.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache"}
SKIP_FILES = {"CHANGELOG.md", "package-lock.json", "rename.py"}
BINARY = (".png", ".jpg", ".jpeg", ".gif", ".zip", ".pyc", ".ico", ".woff", ".woff2")


def find_addon():
    for d in sorted(os.listdir(ROOT)):
        cfg = os.path.join(ROOT, d, "config.yaml")
        if os.path.isfile(cfg):
            text = open(cfg, encoding="utf-8").read()
            slug = re.search(r"^slug:\s*(\S+)", text, re.M)
            name = re.search(r'^name:\s*"?([^"\n]+)"?', text, re.M)
            if slug and name:
                return d, slug.group(1).strip("\"'"), name.group(1).strip()
    sys.exit("Kein Add-on-Ordner mit config.yaml gefunden.")


def slugify(name):
    s = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def walk_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(base, f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help='neuer Anzeigename, z. B. "Mein Name"')
    ap.add_argument("--slug", help="neue Kennung (Kleinbuchstaben, Ziffern, Unterstrich); Standard: aus dem Namen")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts ändern")
    a = ap.parse_args()

    folder, old_slug, old_name = find_addon()
    new_name = a.name.strip()
    new_slug = a.slug or slugify(new_name)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", new_slug):
        sys.exit(f"Ungültige Kennung „{new_slug}“. Erlaubt: Kleinbuchstaben, Ziffern, Unterstrich, am Anfang ein Buchstabe.")
    if not new_name or any(c in new_name for c in '"\\\n'):
        sys.exit("Ungültiger Name.")
    old_prefix = old_name.lower()
    if (old_name, old_slug) == (new_name, new_slug):
        sys.exit("Name und Kennung sind schon so gesetzt.")

    def pascal(n):
        return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9]+", n) if w)

    pairs = []
    # Bezeichner im Code (z. B. Klassenname der Karte) dürfen keine Leerzeichen enthalten
    if pascal(old_name) + "Card" != pascal(new_name) + "Card":
        pairs.append((pascal(old_name) + "Card", pascal(new_name) + "Card"))
    if old_slug != new_slug:
        pairs.append((old_slug, new_slug))
    pairs.append((old_name, new_name))
    pairs.append((old_name.upper(), new_name.upper()))
    if old_prefix != new_slug and old_prefix != old_slug:
        pairs.append((old_prefix, new_slug))
    # Reihenfolge: längste zuerst, damit sich Muster nicht in die Quere kommen
    pairs.sort(key=lambda p: -len(p[0]))
    print(f"Umbenennen: „{old_name}“ ({old_slug}) → „{new_name}“ ({new_slug})")

    def convert(text):
        counts = {}
        # Platzhalter-Technik: erst alle Muster durch eindeutige Marken ersetzen, dann einsetzen (vermeidet Doppelersetzung)
        marks = {}
        for i, (old, new) in enumerate(pairs):
            mark = f"\x00{i}\x00"
            marks[mark] = new
            n = text.count(old)
            if n:
                counts[old] = counts.get(old, 0) + n
                text = text.replace(old, mark)
        for mark, new in marks.items():
            text = text.replace(mark, new)
        return text, counts

    changed, total = [], {}
    for path in walk_files():
        rel = os.path.relpath(path, ROOT)
        base = os.path.basename(path)
        if base in SKIP_FILES or base.lower().endswith(BINARY):
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        new_text, counts = convert(text)
        if new_text != text:
            changed.append(rel)
            for k, v in counts.items():
                total[k] = total.get(k, 0) + v
            if not a.dry_run:
                open(path, "w", encoding="utf-8").write(new_text)
    print(f"{len(changed)} Dateien mit Textänderungen")
    for k, v in sorted(total.items(), key=lambda kv: -kv[1]):
        print(f"  {k!r}: {v} Ersetzungen")

    # Dateien und Ordner umbenennen (tiefste zuerst)
    renames = []
    for base, dirs, files in os.walk(ROOT, topdown=False):
        if any(part in SKIP_DIRS for part in os.path.relpath(base, ROOT).split(os.sep)):
            continue
        for n in files + dirs:
            if n in SKIP_FILES or n.lower().endswith(BINARY):
                continue
            new_n, _ = convert(n)
            if new_n != n:
                renames.append((os.path.join(base, n), os.path.join(base, new_n)))
    in_git = os.path.isdir(os.path.join(ROOT, ".git"))
    for src, dst in renames:
        print(f"  umbenannt: {os.path.relpath(src, ROOT)} → {os.path.relpath(dst, ROOT)}")
        if not a.dry_run:
            if in_git:
                r = subprocess.run(["git", "mv", src, dst], cwd=ROOT, capture_output=True)
                if r.returncode == 0:
                    continue
            os.rename(src, dst)

    new_folder = new_slug if folder == old_slug else folder

    # Logo neu erzeugen
    if not a.dry_run:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            import make_logo
            make_logo.make(new_name, os.path.join(ROOT, new_folder))
            print("  Logo neu erzeugt")
        except ImportError:
            print("  Hinweis: Pillow fehlt, logo.png enthält noch den alten Namen (pip install pillow, dann tools/make_logo.py).")

    print("\nFertig." if not a.dry_run else "\nTrockenlauf, nichts geändert.")
    if not a.dry_run:
        print("Als Nächstes: tools/test_all.sh, dann im CHANGELOG einen Abschnitt zur Umbenennung ergänzen und veröffentlichen.")
        print("Hinweis: Die Kennung ändert sich, Home Assistant sieht ein neues Add-on. Vorher Einstellungen exportieren.")


if __name__ == "__main__":
    main()
