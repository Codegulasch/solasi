"""Lokales Update: ein Repo-Zip hochladen, prüfen und als neuen Stand von SOLASI einspielen (ohne GitHub).

Der Code (app/) wird in den Datenordner entpackt (overlay/current). Das Startprogramm (boot.py) startet SOLASI von dort, solange der Stand
neuer ist als der im Add-on installierte. Der Vorgänger bleibt als overlay/previous erhalten.
Nicht ersetzbar: config.yaml, Dockerfile und Python-Pakete – dafür braucht es ein richtiges Add-on-Update.
"""
import asyncio
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

from util import DATA_DIR

OV = os.path.join(DATA_DIR, "overlay")
META = os.path.join(OV, "meta.json")
CUR = os.path.join(OV, "current")
PREV = os.path.join(OV, "previous")
FAIL = os.path.join(OV, "last_failure.json")
VFILE = ".solasi_version"
MAX_ZIP = 25 * 1024 * 1024
MAX_UNPACKED = 40 * 1024 * 1024
MAX_FILES = 400
OK_EXT = {".py", ".js", ".html", ".css", ".json", ".png", ".svg", ".ico", ".txt", ".md"}
SKIP_PARTS = {"__pycache__", "node_modules", ".git", ".pytest_cache", "tests"}


def vt(v):
    out = []
    for p in str(v).split("."):
        d = "".join(c for c in p if c.isdigit())
        out.append(int(d) if d else 0)
    return tuple(out)


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def image_version():
    return os.environ.get("SOLASI_IMAGE_VERSION") or os.environ.get("SOLASI_VERSION") or "0"


def status():
    m = _load(META) or {}
    pv = ""
    try:
        with open(os.path.join(PREV, VFILE), encoding="utf-8") as f:
            pv = f.read().strip()
    except OSError:
        pass
    return {"image_version": image_version(), "running_version": os.environ.get("SOLASI_VERSION") or "dev",
            "overlay": bool(m and os.path.isdir(CUR)), "overlay_active": os.environ.get("SOLASI_OVERLAY") == "1",
            "overlay_version": m.get("version", ""), "confirmed": bool(m.get("confirmed")), "installed_at": m.get("installed_at", ""),
            "previous_version": pv, "failure": _load(FAIL)}


def confirm():
    """Vom laufenden lokalen Stand nach einer stabilen Minute aufgerufen."""
    m = _load(META)
    if m and os.environ.get("SOLASI_OVERLAY") == "1" and not m.get("confirmed"):
        m["confirmed"] = True
        _save(META, m)
        try:
            os.remove(FAIL)
        except OSError:
            pass
        return True
    return False


def _find_base(names):
    cands = [n for n in names if n == "app/main.py" or n.endswith("/app/main.py")]
    cands = [n for n in cands if not any(p in SKIP_PARTS for p in n.split("/"))]
    if len(cands) != 1:
        return None
    return cands[0][:-len("app/main.py")]


def validate(data, image_ver=None):
    """Zip prüfen. -> (info, Fehlertext). info: {version, files: {Pfad: Name im Zip}, base}."""
    if len(data) > MAX_ZIP:
        return None, "Die Datei ist größer als 25 MB"
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None, "Das ist keine gültige Zip-Datei"
    infos = [i for i in z.infolist() if not i.is_dir()]
    names = [i.filename for i in infos]
    for n in names:
        parts = n.replace("\\", "/").split("/")
        if n.startswith("/") or ".." in parts or ":" in parts[0]:
            return None, f"Unzulässiger Pfad im Zip: {n}"
    for i in infos:
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            return None, f"Verknüpfungen sind nicht erlaubt: {i.filename}"
    base = _find_base(names)
    if base is None:
        return None, "Im Zip fehlt genau eine app/main.py – bitte das Repo-Zip von SOLASI hochladen"
    if base + "config.yaml" not in names:
        return None, "Im Zip fehlt config.yaml neben dem Ordner app"
    cfg = z.read(base + "config.yaml").decode("utf-8", "replace")
    mv = re.search(r'^version:\s*"?([0-9][0-9A-Za-z.\-]*)"?\s*$', cfg, re.M)
    ms = re.search(r"^slug:\s*(\S+)", cfg, re.M)
    if not mv or not ms or ms.group(1).strip("\"'") != "solasi":
        return None, "config.yaml gehört nicht zu SOLASI (Version oder Name fehlt)"
    version = mv.group(1)
    img = image_ver if image_ver is not None else image_version()
    if vt(version) <= vt(img):
        return None, f"Version {version} ist nicht höher als der installierte Stand {img}. Erhöhe die Version in config.yaml"
    files, total = {}, 0
    for i in infos:
        n = i.filename
        if not n.startswith(base + "app/"):
            continue
        rel = n[len(base):]
        if any(p in SKIP_PARTS for p in rel.split("/")):
            continue
        if os.path.splitext(rel)[1].lower() not in OK_EXT:
            return None, f"Dateityp nicht erlaubt: {rel}"
        total += i.file_size
        files[rel] = n
    if len(files) > MAX_FILES or total > MAX_UNPACKED:
        return None, "Zu viele oder zu große Dateien im Zip"
    for req in ("app/main.py", "app/controller.py", "app/boot.py", "app/static/index.html"):
        if req not in files:
            return None, f"Pflichtdatei fehlt: {req}"
    for rel, n in files.items():
        if rel.endswith(".py"):
            try:
                compile(z.read(n).decode("utf-8"), rel, "exec")
            except SyntaxError as e:
                return None, f"Syntaxfehler in {rel}, Zeile {e.lineno}: {e.msg}"
            except UnicodeDecodeError:
                return None, f"{rel} ist kein gültiger Text (UTF-8)"
    return {"version": version, "files": files, "base": base, "total": total}, ""


def _smoke_code(stage):
    return ("import sys, importlib, os\n"
            f"sys.path.insert(0, {stage!r})\n"
            f"mods = sorted(f[:-3] for f in os.listdir({stage!r}) if f.endswith('.py') and f not in ('boot.py',))\n"
            "for m in mods:\n    importlib.import_module(m)\n"
            "print('OK', len(mods))\n")


async def stage_and_test(data, info):
    """Entpackt nach overlay/staging und importiert alle Module in einem eigenen Prozess. -> (Pfad, Fehlertext)."""
    stage_root = os.path.join(OV, "staging")
    shutil.rmtree(stage_root, ignore_errors=True)
    stage = os.path.join(stage_root, "app")
    z = zipfile.ZipFile(io.BytesIO(data))
    for rel, n in info["files"].items():
        dst = os.path.join(stage_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(z.read(n))
    tmp = tempfile.mkdtemp(prefix="solasi-smoke-")
    try:
        env = {"PATH": os.environ.get("PATH", ""), "SOLASI_DATA": tmp, "SOLASI_CONFIG": os.path.join(tmp, "s.json"),
               "SOLASI_VERSION": info["version"], "PYTHONDONTWRITEBYTECODE": "1"}
        proc = await asyncio.create_subprocess_exec(sys.executable, "-I", "-c", _smoke_code(stage), env=env, cwd=tmp,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), 40)
        except asyncio.TimeoutError:
            proc.kill()
            shutil.rmtree(stage_root, ignore_errors=True)
            return None, "Der Test-Import hat zu lange gedauert"
        if proc.returncode != 0:
            tail = out.decode("utf-8", "replace").strip().splitlines()[-4:]
            shutil.rmtree(stage_root, ignore_errors=True)
            return None, "Der Test-Import ist fehlgeschlagen: " + " | ".join(tail)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return stage, ""


def install(stage, info):
    """Stage wird zum aktuellen Stand, der bisherige zum Vorgänger."""
    with open(os.path.join(stage, VFILE), "w", encoding="utf-8") as f:
        f.write(info["version"])
    shutil.rmtree(PREV, ignore_errors=True)
    if os.path.isdir(CUR):
        os.replace(CUR, PREV)
    os.replace(stage, CUR)
    shutil.rmtree(os.path.dirname(stage), ignore_errors=True)
    _save(META, {"version": info["version"], "confirmed": False, "installed_at": time.strftime("%d.%m.%Y %H:%M")})
    try:
        os.remove(FAIL)
    except OSError:
        pass


def rollback(to="image"):
    """to='image': lokalen Stand entfernen. to='previous': Vorgänger wieder einsetzen. -> (ok, Text)."""
    if to == "previous":
        if not os.path.isfile(os.path.join(PREV, "main.py")):
            return False, "Es gibt keinen Vorgänger"
        try:
            with open(os.path.join(PREV, VFILE), encoding="utf-8") as f:
                pv = f.read().strip()
        except OSError:
            return False, "Vorgänger-Version unbekannt"
        tmp = os.path.join(OV, "swap")
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.isdir(CUR):
            os.replace(CUR, tmp)
        os.replace(PREV, CUR)
        if os.path.isdir(tmp):
            os.replace(tmp, PREV)
        _save(META, {"version": pv, "confirmed": False, "installed_at": time.strftime("%d.%m.%Y %H:%M")})
        return True, f"Vorgänger {pv} wird gestartet"
    shutil.rmtree(CUR, ignore_errors=True)
    try:
        os.remove(META)
    except OSError:
        pass
    return True, "Der installierte Stand wird gestartet"
