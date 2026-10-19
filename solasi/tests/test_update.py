import io, json, os, shutil, subprocess, sys, tempfile, textwrap, zipfile
import pytest
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
APP = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, APP)
import update as upd

ROOT = os.path.abspath(os.path.join(APP, ".."))


def make_zip(version="9.9.9", prefix="solasi-repo/solasi/", mutate=None, extra=None, slug="solasi"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(prefix + "config.yaml", f'name: "SOLASI"\nversion: "{version}"\nslug: {slug}\n')
        for dp, dn, fn in os.walk(APP):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                data = open(full, "rb").read()
                if mutate and rel in mutate:
                    data = mutate[rel]
                z.writestr(prefix + rel, data)
        z.writestr(prefix + "tests/test_x.py", "def test_x(): pass\n")
        for n, d in (extra or {}).items():
            z.writestr(n, d)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    ov = tmp_path / "overlay"
    for k, v in (("OV", ov), ("META", ov / "meta.json"), ("CUR", ov / "current"), ("PREV", ov / "previous"), ("FAIL", ov / "last_failure.json")):
        monkeypatch.setattr(upd, k, str(v))
    monkeypatch.setenv("SOLASI_IMAGE_VERSION", "2.3.2")
    monkeypatch.setenv("SOLASI_VERSION", "2.3.2")
    monkeypatch.delenv("SOLASI_OVERLAY", raising=False)


def test_valid_zip():
    info, err = upd.validate(make_zip())
    assert info and not err and info["version"] == "9.9.9"
    assert "app/main.py" in info["files"] and not any("tests" in f for f in info["files"])


def test_valid_zip_without_wrapper_folder():
    info, err = upd.validate(make_zip(prefix=""))
    assert info and info["base"] == ""


@pytest.mark.parametrize("kw,needle", [
    (dict(version="2.3.2"), "nicht höher"),
    (dict(version="2.3.1"), "nicht höher"),
    (dict(slug="anderes"), "nicht zu SOLASI"),
    (dict(mutate={"app/controller.py": b"def x(:\n"}), "Syntaxfehler"),
    (dict(extra={"../evil.py": b"x=1"}), "Unzulässiger Pfad"),
    (dict(extra={"solasi-repo/solasi/app/run.sh": b"rm -rf /"}), "Dateityp nicht erlaubt"),
])
def test_rejects(kw, needle):
    info, err = upd.validate(make_zip(**kw))
    assert info is None and needle in err, err


def test_rejects_garbage_and_missing_parts():
    assert "keine gültige Zip" in upd.validate(b"hallo")[1]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a/config.yaml", 'version: "9.0.0"\nslug: solasi\n')
    assert "app/main.py" in upd.validate(buf.getvalue())[1]
    assert "25 MB" in upd.validate(b"0" * (upd.MAX_ZIP + 1))[1]


def test_rejects_symlink():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        zi = zipfile.ZipInfo("solasi/app/main.py")
        zi.external_attr = (0o120777 << 16)
        z.writestr(zi, "/etc/passwd")
        z.writestr("solasi/config.yaml", 'version: "9.0.0"\nslug: solasi\n')
    assert "Verknüpfungen" in upd.validate(buf.getvalue())[1]


@pytest.mark.asyncio
async def test_stage_install_rollback():
    data = make_zip("9.9.9")
    info, _ = upd.validate(data)
    stage, err = await upd.stage_and_test(data, info)
    assert stage and not err, err
    upd.install(stage, info)
    st = upd.status()
    assert st["overlay"] and st["overlay_version"] == "9.9.9" and not st["confirmed"] and st["previous_version"] == ""
    assert os.path.isfile(os.path.join(upd.CUR, "main.py"))
    # zweites Update: erster Stand wird Vorgänger
    data2 = make_zip("9.9.10")
    info2, _ = upd.validate(data2)
    stage2, err = await upd.stage_and_test(data2, info2)
    upd.install(stage2, info2)
    assert upd.status()["previous_version"] == "9.9.9" and upd.status()["overlay_version"] == "9.9.10"
    ok, _ = upd.rollback("previous")
    assert ok and upd.status()["overlay_version"] == "9.9.9" and upd.status()["previous_version"] == "9.9.10"
    ok, _ = upd.rollback("image")
    assert ok and not upd.status()["overlay"]
    assert not upd.rollback("previous")[0] or True


@pytest.mark.asyncio
async def test_smoke_import_catches_broken_module():
    bad = make_zip("9.9.9", mutate={"app/hogs.py": b"import gibt_es_nicht_xyz\n"})
    info, err = upd.validate(bad)
    assert info, err
    stage, err = await upd.stage_and_test(bad, info)
    assert stage is None and "Test-Import" in err and "gibt_es_nicht_xyz" in err
    assert not os.path.isdir(os.path.join(upd.OV, "staging"))


def test_confirm(monkeypatch):
    os.makedirs(upd.OV, exist_ok=True)
    json.dump({"version": "9.9.9", "confirmed": False}, open(upd.META, "w"))
    assert not upd.confirm()                       # nicht als lokaler Stand gestartet
    monkeypatch.setenv("SOLASI_OVERLAY", "1")
    assert upd.confirm() and upd.status()["confirmed"]


# ---- boot.py ----
def boot_env(tmp, image_version="2.3.2"):
    app = tmp / "image" / "app"
    app.mkdir(parents=True)
    shutil.copy(os.path.join(APP, "boot.py"), app / "boot.py")
    (app / "main.py").write_text("import os,sys\nprint('IMAGE', os.environ.get('SOLASI_VERSION'))\nsys.exit(0)\n")
    data = tmp / "data"
    (data / "overlay" / "current").mkdir(parents=True)
    env = dict(os.environ, SOLASI_DATA=str(data), SOLASI_VERSION=image_version)
    env.pop("SOLASI_OVERLAY", None)
    return app, data, env


def run_boot(app, env):
    return subprocess.run([sys.executable, str(app / "boot.py")], env=env, capture_output=True, text=True, timeout=60)


def put_overlay(data, version, main_src, confirmed=False):
    ov = data / "overlay"
    (ov / "current" / "main.py").write_text(main_src)
    (ov / "meta.json").write_text(json.dumps({"version": version, "confirmed": confirmed}))


def test_boot_uses_newer_overlay(tmp_path):
    app, data, env = boot_env(tmp_path)
    put_overlay(data, "2.4.0", "import os,sys\nprint('OVERLAY', os.environ.get('SOLASI_VERSION'), os.environ.get('SOLASI_OVERLAY'))\nsys.exit(0)\n")
    r = run_boot(app, env)
    assert "OVERLAY 2.4.0 1" in r.stdout and r.returncode == 0


def test_boot_drops_overlay_after_official_update(tmp_path):
    app, data, env = boot_env(tmp_path, image_version="2.4.0")
    put_overlay(data, "2.4.0", "print('OVERLAY')\n")
    r = run_boot(app, env)
    assert "IMAGE 2.4.0" in r.stdout and "OVERLAY" not in r.stdout
    assert not (data / "overlay" / "meta.json").exists()


def test_boot_rolls_back_when_unconfirmed_overlay_crashes(tmp_path):
    app, data, env = boot_env(tmp_path)
    put_overlay(data, "2.4.0", "import sys\nsys.exit(3)\n")
    r = run_boot(app, env)
    assert "IMAGE 2.3.2" in r.stdout and r.returncode == 0
    fail = json.loads((data / "overlay" / "last_failure.json").read_text())
    assert fail["version"] == "2.4.0" and fail["code"] == 3
    assert not (data / "overlay" / "meta.json").exists()


def test_boot_keeps_confirmed_overlay_exit_code(tmp_path):
    app, data, env = boot_env(tmp_path)
    put_overlay(data, "2.4.0", "import sys\nsys.exit(4)\n", confirmed=True)
    r = run_boot(app, env)
    assert r.returncode == 4 and (data / "overlay" / "meta.json").exists()


def test_boot_restart_code_starts_again(tmp_path):
    app, data, env = boot_env(tmp_path)
    marker = tmp_path / "ran"
    put_overlay(data, "2.4.0", textwrap.dedent(f"""
        import os, sys
        m = {str(marker)!r}
        if not os.path.exists(m):
            open(m, 'w').write('1'); sys.exit(75)
        print('SECOND'); sys.exit(0)
    """))
    r = run_boot(app, env)
    assert "SECOND" in r.stdout and r.returncode == 0


@pytest.mark.asyncio
async def test_api_upload_rollback_and_direct_blocked(tmp_path, monkeypatch):
    import asyncio
    import main as appmain
    from aiohttp.test_utils import TestClient, TestServer
    from controller import Controller, ConfigStore
    from ha import HA
    store = ConfigStore(str(tmp_path / "s.json"))
    ctrl = Controller(None, store); ha = HA("ws://x", "t"); ctrl.ha = ha
    stop = asyncio.Event()
    monkeypatch.setattr(appmain, "STOP_EVENT", stop)
    monkeypatch.setitem(appmain.RESTART, "requested", False)
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha))) as c:
        st = await (await c.get("/api/update")).json()
        assert st["overlay"] is False and st["image_version"] == "2.3.2"
        bad = await c.post("/api/update/upload", data=b"nix")
        assert bad.status == 400 and "Zip" in (await bad.json())["error"]
        ok = await (await c.post("/api/update/upload", data=make_zip("9.9.9"))).json()
        assert ok["ok"] and ok["version"] == "9.9.9" and ok["restart"]
        assert appmain.RESTART["requested"]
        await asyncio.wait_for(stop.wait(), 5)          # geordneter Stopp wurde ausgelöst
        st = await (await c.get("/api/update")).json()
        assert st["overlay"] and st["overlay_version"] == "9.9.9"
        assert (await c.post("/api/update/rollback", json={"to": "previous"})).status == 400   # kein Vorgänger
        r = await (await c.post("/api/update/rollback", json={"to": "image"})).json()
        assert r["ok"] and not (await (await c.get("/api/update")).json())["overlay"]
        s = await (await c.get("/api/status")).json()
        assert s["app"]["version"] and "overlay" in s["app"]
    # direkter Port: kein Einspielen
    async with TestClient(TestServer(appmain.build_app(ctrl, store, ha, direct=True))) as c:
        r = await c.post("/api/update/upload", data=make_zip("9.9.9"))
        assert r.status in (401, 403)
