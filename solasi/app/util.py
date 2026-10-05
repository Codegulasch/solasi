"""Kleine Hilfen: Datenordner, Zeitzone, JSON-Dateien."""
import json
import os
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

DATA_DIR = os.environ.get("SOLASI_DATA", "/data")
_tz = None


def set_timezone(name):
    global _tz
    try:
        _tz = ZoneInfo(name) if (ZoneInfo and name) else None
    except Exception:  # noqa: BLE001
        _tz = None


def now_local():
    return datetime.now(_tz or timezone.utc)


def data_path(name):
    return os.path.join(DATA_DIR, name)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass
