import json
import re
import subprocess


class FFmpegError(Exception):
    pass


def get_audio_duration(path: str) -> float:
    """Runs ffprobe on the given audio file and returns its duration in seconds."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                path,
            ],
            capture_output=True,
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise FFmpegError(f"ffprobe failed for {path}: {exc}") from exc

    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise FFmpegError(f"Could not parse ffprobe output for {path}: {exc}") from exc


def _escape_drawtext(text: str) -> str:
    """Escapes special characters for use inside an ffmpeg drawtext filter value."""
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")
    text = text.replace("%", "\\%")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace(",", "\\,")
    text = text.replace("\n", " ")
    return text


def _caption_chunks(script: str, total_duration: float) -> list[tuple[str, float, float]]:
    """Splits the script into ~5-word chunks, timed evenly across the duration."""
    words = re.findall(r"\S+", script)
    if not words:
        return []

    chunk_size = 5
    chunks = [
        " ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)
    ]

    per_chunk = total_duration / len(chunks)
    timed: list[tuple[str, float, float]] = []
    for i, chunk in enumerate(chunks):
        start = i * per_chunk
        end = total_duration if i == len(chunks) - 1 else (i + 1) * per_chunk
        timed.append((chunk, start, end))
    return timed


FPS = 25
WIDTH = 1080
HEIGHT = 1920
FONT_FILE = "C\\:/Windows/Fonts/arial.ttf"


def build_video(images: list[str], audio_path: str, output_path: str, script: str) -> None:
    """Assembles a vertical (1080x1920) video from images + voiceover + burned-in captions."""
    if not images:
        raise FFmpegError("At least one image is required to build a video")

    audio_duration = get_audio_duration(audio_path)
    per_image_duration = audio_duration / len(images)
    frames_per_image = max(1, round(per_image_duration * FPS))

    cmd: list[str] = ["ffmpeg", "-y"]

    for image_path in images:
        cmd += [
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-t",
            f"{per_image_duration:.3f}",
            "-i",
            image_path,
        ]

    audio_input_index = len(images)
    cmd += ["-i", audio_path]

    filter_parts: list[str] = []
    for i in range(len(images)):
        filter_parts.append(
            f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={frames_per_image}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"setsar=1[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
    filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[vconcat]")

    captions = _caption_chunks(script, audio_duration)
    last_label = "vconcat"
    for idx, (text, start, end) in enumerate(captions):
        escaped = _escape_drawtext(text)
        out_label = f"vcap{idx}"
        filter_parts.append(
            f"[{last_label}]drawtext=text='{escaped}':fontfile='{FONT_FILE}':"
            f"fontcolor=white:fontsize=64:"
            f"box=1:boxcolor=black@0.5:boxborderw=24:"
            f"x=(w-text_w)/2:y=h-300:"
            f"enable='between(t,{start:.3f},{end:.3f})'[{out_label}]"
        )
        last_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{last_label}]",
        "-map",
        f"{audio_input_index}:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise FFmpegError(f"ffmpeg failed: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise FFmpegError(f"ffmpeg not found: {exc}") from exc
