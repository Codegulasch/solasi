"""Startprogramm von SOLASI.

Startet SOLASI aus dem lokal eingespielten Stand (Update per Zip-Upload, liegt im Datenordner), sonst aus dem Stand im Image.
Ist der lokale Stand neuer als das Image, wird er benutzt; hat das Add-on selbst ein Update bekommen (gleiche oder höhere Version),
wird der lokale Stand verworfen. Stürzt ein frisch eingespielter Stand ab, bevor er sich als stabil gemeldet hat,
wird sofort auf den Stand im Image zurückgegangen. Der Code ist absichtlich klein und hängt von nichts ab.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("SOLASI_DATA", "/data")
OV = os.path.join(DATA, "overlay")
META = os.path.join(OV, "meta.json")
CUR = os.path.join(OV, "current")
FAIL = os.path.join(OV, "last_failure.json")
RESTART_CODE = 75


def vt(v):
    out = []
    for p in str(v).split("."):
        d = "".join(c for c in p if c.isdigit())
        out.append(int(d) if d else 0)
    return tuple(out)


def image_version():
    v = os.environ.get("SOLASI_VERSION")
    if v:
        return v
    try:
        with open(os.path.join(HERE, "..", "config.yaml"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return "0"


def read_meta():
    try:
        with open(META, encoding="utf-8") as f:
            m = json.load(f)
        return m if isinstance(m, dict) else None
    except (OSError, ValueError):
        return None


def drop_overlay(reason=None):
    shutil.rmtree(CUR, ignore_errors=True)
    try:
        os.remove(META)
    except OSError:
        pass
    if reason:
        try:
            with open(FAIL, "w", encoding="utf-8") as f:
                json.dump(reason, f, ensure_ascii=False)
        except OSError:
            pass


def pick_overlay(img):
    """-> Meta des lokalen Stands, wenn er benutzt werden soll, sonst None."""
    m = read_meta()
    if not m or not os.path.isfile(os.path.join(CUR, "main.py")):
        return None
    if vt(m.get("version", "0")) <= vt(img):
        print(f"[boot] Add-on-Update ({img}) ist nicht älter als der lokale Stand ({m.get('version')}): lokaler Stand wird entfernt", flush=True)
        drop_overlay()
        return None
    return m


def main():
    img = image_version()
    state = {"child": None, "stop": False}

    def on_sig(sig, _frame):
        state["stop"] = True
        if state["child"] and state["child"].poll() is None:
            state["child"].send_signal(signal.SIGTERM)

    signal.signal(signal.SIGTERM, on_sig)
    signal.signal(signal.SIGINT, on_sig)
    while True:
        m = pick_overlay(img)
        env = dict(os.environ)
        env["SOLASI_IMAGE_VERSION"] = img
        if m:
            path = CUR
            env["SOLASI_VERSION"] = str(m.get("version"))
            env["SOLASI_OVERLAY"] = "1"
        else:
            path = HERE
            env.pop("SOLASI_OVERLAY", None)
        t0 = time.time()
        print(f"[boot] Starte SOLASI {env.get('SOLASI_VERSION', img)} ({'lokaler Stand' if m else 'Stand im Add-on'})", flush=True)
        state["child"] = subprocess.Popen([sys.executable, "-u", os.path.join(path, "main.py")], cwd=path, env=env)
        rc = state["child"].wait()
        if state["stop"]:
            sys.exit(rc if rc is not None else 0)
        if rc == RESTART_CODE:
            continue
        if m:
            cur = read_meta() or {}
            if not cur.get("confirmed"):
                reason = {"version": m.get("version"), "at": time.strftime("%d.%m. %H:%M:%S"), "code": rc,
                          "seconds": round(time.time() - t0),
                          "reason": f"Der lokale Stand {m.get('version')} beendete sich nach {round(time.time() - t0)} s mit Code {rc}, bevor er stabil lief"}
                print("[boot] " + reason["reason"] + " – zurück auf den Stand im Add-on", flush=True)
                drop_overlay(reason)
                continue
        sys.exit(rc)


if __name__ == "__main__":
    main()
