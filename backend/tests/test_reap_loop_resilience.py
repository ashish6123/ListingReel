"""Tests that the background reaper loop in app.main survives a crash in a
single iteration instead of silently dying (which would be exactly the kind
of "background task disappears with no trace" bug this loop was built to
catch elsewhere)."""

import pytest

from app import main as main_module


class _StopLoop(Exception):
    """Raised by the fake sleep to end the infinite loop after N iterations."""


@pytest.mark.asyncio
async def test_reap_loop_logs_and_continues_after_exception(monkeypatch):
    calls = {"reap": 0, "sleep": 0}

    def fake_reap(db):
        calls["reap"] += 1
        raise RuntimeError("boom")

    async def fake_sleep(seconds):
        calls["sleep"] += 1
        raise _StopLoop()

    monkeypatch.setattr(main_module, "reap_stuck_videos", fake_reap)
    monkeypatch.setattr(main_module, "get_db", lambda: object())
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoop):
        await main_module._reap_loop()

    assert calls["reap"] == 1
    assert calls["sleep"] == 1


@pytest.mark.asyncio
async def test_reap_loop_runs_multiple_iterations(monkeypatch):
    calls = {"reap": 0, "sleep": 0}

    def fake_reap(db):
        calls["reap"] += 1
        return 0

    async def fake_sleep(seconds):
        calls["sleep"] += 1
        if calls["sleep"] >= 3:
            raise _StopLoop()

    monkeypatch.setattr(main_module, "reap_stuck_videos", fake_reap)
    monkeypatch.setattr(main_module, "get_db", lambda: object())
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoop):
        await main_module._reap_loop()

    assert calls["reap"] == 3
    assert calls["sleep"] == 3


@pytest.mark.asyncio
async def test_reap_loop_sleeps_for_configured_interval(monkeypatch):
    captured = {}

    def fake_reap(db):
        return 0

    async def fake_sleep(seconds):
        captured["seconds"] = seconds
        raise _StopLoop()

    monkeypatch.setattr(main_module, "reap_stuck_videos", fake_reap)
    monkeypatch.setattr(main_module, "get_db", lambda: object())
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoop):
        await main_module._reap_loop()

    assert captured["seconds"] == main_module.REAP_INTERVAL_SECONDS
