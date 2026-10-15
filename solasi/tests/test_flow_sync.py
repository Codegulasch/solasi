import os, subprocess, sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "tools", "sync_flow.py")


@pytest.mark.skipif(not os.path.exists(SCRIPT), reason="tools/ ist nur im Repository vorhanden")
def test_flow_grafik_in_app_und_karte_identisch():
    r = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True)
    assert r.returncode == 0, "Energiefluss-Code weicht ab, `python tools/sync_flow.py` ausführen: " + r.stdout
