"""Tests for app.services.ffmpeg, including:
- the memory-reduction fix (720x1280, veryfast preset, single thread) that
  stops Render's free-tier instance from OOM-killing the container mid-encode
- existing timeout/error handling on both subprocess calls
- caption-chunking and drawtext-escaping edge cases
"""

import json
import subprocess

import pytest

from app.services import ffmpeg


# ---------------------------------------------------------------------------
# get_audio_duration
# ---------------------------------------------------------------------------


class _FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout


def test_get_audio_duration_parses_ffprobe_output(monkeypatch):
    payload = json.dumps({"format": {"duration": "12.345"}})
    monkeypatch.setattr(
        ffmpeg.subprocess, "run", lambda *a, **k: _FakeCompletedProcess(payload)
    )

    duration = ffmpeg.get_audio_duration("fake.mp3")

    assert duration == pytest.approx(12.345)


def test_get_audio_duration_passes_explicit_timeout(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return _FakeCompletedProcess(json.dumps({"format": {"duration": "1.0"}}))

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)
    ffmpeg.get_audio_duration("fake.mp3")

    assert captured["timeout"] == ffmpeg.PROBE_TIMEOUT_SECONDS


def test_get_audio_duration_raises_on_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=30)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError, match="timed out"):
        ffmpeg.get_audio_duration("fake.mp3")


def test_get_audio_duration_raises_on_called_process_error(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="ffprobe")

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError):
        ffmpeg.get_audio_duration("fake.mp3")


def test_get_audio_duration_raises_when_ffprobe_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ffprobe not found")

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError):
        ffmpeg.get_audio_duration("fake.mp3")


def test_get_audio_duration_raises_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        ffmpeg.subprocess, "run", lambda *a, **k: _FakeCompletedProcess("not json")
    )

    with pytest.raises(ffmpeg.FFmpegError, match="parse"):
        ffmpeg.get_audio_duration("fake.mp3")


def test_get_audio_duration_raises_when_duration_key_missing(monkeypatch):
    monkeypatch.setattr(
        ffmpeg.subprocess,
        "run",
        lambda *a, **k: _FakeCompletedProcess(json.dumps({"format": {}})),
    )

    with pytest.raises(ffmpeg.FFmpegError, match="parse"):
        ffmpeg.get_audio_duration("fake.mp3")


# ---------------------------------------------------------------------------
# _escape_drawtext
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("hello", "hello"),
        ("50% off", "50\\% off"),
        ("a:b", "a\\:b"),
        ("it's nice", "it’s nice"),
        ("[bracket]", "\\[bracket\\]"),
        ("a,b,c", "a\\,b\\,c"),
        ("line\nbreak", "line break"),
        ("back\\slash", "back\\\\slash"),
    ],
)
def test_escape_drawtext_handles_special_characters(raw, expected):
    assert ffmpeg._escape_drawtext(raw) == expected


# ---------------------------------------------------------------------------
# _caption_chunks
# ---------------------------------------------------------------------------


def test_caption_chunks_empty_script_returns_no_chunks():
    assert ffmpeg._caption_chunks("", 10.0) == []


def test_caption_chunks_whitespace_only_script_returns_no_chunks():
    assert ffmpeg._caption_chunks("   \n  ", 10.0) == []


def test_caption_chunks_groups_five_words_per_chunk():
    script = " ".join(f"word{i}" for i in range(12))  # 12 words -> 3 chunks
    chunks = ffmpeg._caption_chunks(script, 30.0)

    assert len(chunks) == 3
    assert chunks[0][0] == "word0 word1 word2 word3 word4"
    assert chunks[1][0] == "word5 word6 word7 word8 word9"
    assert chunks[2][0] == "word10 word11"


def test_caption_chunks_timing_spans_full_duration_with_no_gaps():
    script = " ".join(f"word{i}" for i in range(10))
    chunks = ffmpeg._caption_chunks(script, 20.0)

    assert chunks[0][1] == 0.0
    assert chunks[-1][2] == 20.0
    for i in range(len(chunks) - 1):
        assert chunks[i][2] == chunks[i + 1][1]


def test_caption_chunks_single_word():
    chunks = ffmpeg._caption_chunks("hi", 5.0)

    assert len(chunks) == 1
    assert chunks[0] == ("hi", 0.0, 5.0)


# ---------------------------------------------------------------------------
# build_video - memory/resolution fix + error handling
# ---------------------------------------------------------------------------


@pytest.fixture
def no_real_ffprobe(monkeypatch):
    monkeypatch.setattr(ffmpeg, "get_audio_duration", lambda path: 10.0)


def test_build_video_raises_when_no_images(no_real_ffprobe):
    with pytest.raises(ffmpeg.FFmpegError, match="At least one image"):
        ffmpeg.build_video([], "audio.mp3", "out.mp4", "script")


def test_build_video_uses_720x1280_resolution(no_real_ffprobe, monkeypatch):
    """Regression test for the OOM fix: encoding at 1080x1920 was crashing
    the Render container mid-encode. Resolution must stay at 720x1280."""
    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")

    filter_complex = captured_cmd["cmd"][captured_cmd["cmd"].index("-filter_complex") + 1]
    assert "scale=720:1280" in filter_complex
    assert "scale=1080:1920" not in filter_complex


def test_build_video_uses_low_memory_encode_flags(no_real_ffprobe, monkeypatch):
    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")

    cmd = captured_cmd["cmd"]
    assert "-preset" in cmd and cmd[cmd.index("-preset") + 1] == "veryfast"
    assert "-threads" in cmd and cmd[cmd.index("-threads") + 1] == "1"


def test_build_video_passes_explicit_encode_timeout(no_real_ffprobe, monkeypatch):
    captured_kwargs = {}

    def fake_run(cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")

    assert captured_kwargs["timeout"] == ffmpeg.ENCODE_TIMEOUT_SECONDS


def test_build_video_raises_on_encode_timeout(no_real_ffprobe, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=180)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError, match="timed out"):
        ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")


def test_build_video_raises_on_encode_failure_with_stderr(no_real_ffprobe, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1, cmd="ffmpeg", stderr="invalid codec"
        )

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError, match="invalid codec"):
        ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")


def test_build_video_raises_when_ffmpeg_missing(no_real_ffprobe, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("ffmpeg not found")

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    with pytest.raises(ffmpeg.FFmpegError, match="not found"):
        ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "hello world")


def test_build_video_handles_multiple_images(no_real_ffprobe, monkeypatch):
    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    ffmpeg.build_video(
        ["img1.jpg", "img2.jpg", "img3.jpg"], "audio.mp3", "out.mp4", "hello world"
    )

    cmd = captured_cmd["cmd"]
    assert cmd.count("-loop") == 3
    filter_complex = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=3" in filter_complex


def test_build_video_handles_empty_script_with_no_captions(no_real_ffprobe, monkeypatch):
    """No captions should be burned in for an empty script, but the video
    must still build successfully (no drawtext filters)."""
    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    ffmpeg.build_video(["img1.jpg"], "audio.mp3", "out.mp4", "")

    filter_complex = captured_cmd["cmd"][captured_cmd["cmd"].index("-filter_complex") + 1]
    assert "drawtext" not in filter_complex
