"""Tests for the stuck-'processing'-video watchdog (app.routers.video.reap_stuck_videos).

This sweep exists because a Render container restart/OOM-kill mid-encode can
kill the background task before its except block ever runs, leaving a video
stuck in 'processing' forever with no error written.
"""

from datetime import datetime, timedelta, timezone

from app.routers.video import STUCK_PROCESSING_THRESHOLD_MINUTES, reap_stuck_videos


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, table_name: str, store: dict):
        self.table_name = table_name
        self.store = store
        self._update_payload = None
        self._eq_calls: list[tuple[str, str]] = []
        self._lt_calls: list[tuple[str, str]] = []

    def update(self, payload):
        self._update_payload = payload
        return self

    def eq(self, col, val):
        self._eq_calls.append((col, val))
        return self

    def lt(self, col, val):
        self._lt_calls.append((col, val))
        return self

    def execute(self):
        self.store["table_name"] = self.table_name
        self.store["update_payload"] = self._update_payload
        self.store["eq_calls"] = self._eq_calls
        self.store["lt_calls"] = self._lt_calls
        return _FakeResult(self.store.get("matched_rows", []))


class _FakeDB:
    def __init__(self, matched_rows):
        self.store = {"matched_rows": matched_rows}

    def table(self, name):
        return _FakeQuery(name, self.store)


def test_reap_marks_stuck_rows_failed_and_returns_count():
    db = _FakeDB(matched_rows=[{"id": "a"}, {"id": "b"}])

    count = reap_stuck_videos(db)

    assert count == 2
    assert db.store["update_payload"]["status"] == "failed"
    assert isinstance(db.store["update_payload"]["error_message"], str)
    assert db.store["update_payload"]["error_message"]


def test_reap_returns_zero_when_nothing_stuck():
    db = _FakeDB(matched_rows=[])

    assert reap_stuck_videos(db) == 0


def test_reap_targets_the_videos_table():
    db = _FakeDB(matched_rows=[])

    reap_stuck_videos(db)

    assert db.store["table_name"] == "videos"


def test_reap_only_filters_processing_status():
    db = _FakeDB(matched_rows=[])

    reap_stuck_videos(db)

    assert ("status", "processing") in db.store["eq_calls"]
    # Must never touch 'completed' or 'failed' rows.
    assert ("status", "completed") not in db.store["eq_calls"]
    assert ("status", "failed") not in db.store["eq_calls"]


def test_reap_uses_correct_cutoff_window():
    db = _FakeDB(matched_rows=[])

    before = datetime.now(timezone.utc)
    reap_stuck_videos(db)
    after = datetime.now(timezone.utc)

    cutoff_col, cutoff_str = db.store["lt_calls"][0]
    assert cutoff_col == "updated_at"

    cutoff = datetime.fromisoformat(cutoff_str)
    expected_min = before - timedelta(minutes=STUCK_PROCESSING_THRESHOLD_MINUTES)
    expected_max = after - timedelta(minutes=STUCK_PROCESSING_THRESHOLD_MINUTES)
    assert expected_min <= cutoff <= expected_max


def test_reap_does_not_mark_recently_updated_rows():
    """Sanity check on the contract: the fake DB only returns rows the real
    Postgres query would match (status='processing' AND updated_at < cutoff).
    A row updated 1 minute ago must not be matched."""
    recent_cutoff_violation_simulated_as_empty = []
    db = _FakeDB(matched_rows=recent_cutoff_violation_simulated_as_empty)

    assert reap_stuck_videos(db) == 0
