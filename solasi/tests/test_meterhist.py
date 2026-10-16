import os, sys, tempfile
os.environ.setdefault("SOLASI_DATA", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import meterhist
from datetime import datetime, timezone, timedelta
from util import now_local


def ts(d, h):
    return datetime.fromisoformat(f"{d}T{h:02d}:00:00").replace(tzinfo=now_local().tzinfo or timezone.utc).timestamp()


def test_history_tagesdifferenz():
    pts = [(ts("2026-10-01", 6), "100"), (ts("2026-10-01", 23), "101.5"), (ts("2026-10-02", 8), "102"), (ts("2026-10-02", 22), "103"), (ts("2026-10-03", 1), "unavailable")]
    d = meterhist.daily_from_history(pts)
    assert d["2026-10-01"] == 1.5 and round(d["2026-10-02"], 3) == 1.5 and "2026-10-03" not in d


def test_history_ruecksetzen_nicht_negativ():
    pts = [(ts("2026-10-01", 6), "500"), (ts("2026-10-02", 6), "3")]
    assert meterhist.daily_from_history(pts)["2026-10-02"] == 0.0


def test_stats_summe_je_tag():
    rows = [{"start": ts("2026-10-01", 5) * 1000, "change": 0.2}, {"start": ts("2026-10-01", 6) * 1000, "change": 0.3}, {"start": ts("2026-10-02", 6) * 1000, "change": -1}]
    d = meterhist.daily_from_stats(rows)
    assert round(d["2026-10-01"], 3) == 0.5 and d["2026-10-02"] == 0.0


def test_fill_luckenlos():
    f = meterhist.fill({}, 7)
    assert len(f) == 7 and all(x["value"] is None for x in f) and f[-1]["date"] == now_local().strftime("%Y-%m-%d")
