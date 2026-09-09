from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "output" / "reel.mp4"
TEMP = ROOT / "output" / "reel-unique.mp4"
REPORT = ROOT / "variation-report.json"


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    video_stream = next(stream for stream in data["streams"] if stream.get("codec_type") == "video")
    has_audio = any(stream.get("codec_type") == "audio" for stream in data["streams"])
    duration = float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0.0)
    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "duration": duration,
        "has_audio": has_audio,
    }


def even(value: float) -> int:
    number = int(math.ceil(value))
    return number if number % 2 == 0 else number + 1


def choose(seed: str, values: list):
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return values[int.from_bytes(digest[:4], "big") % len(values)]


def differentiate(path: Path = VIDEO) -> dict:
    platform = os.environ.get("PLATFORM", "unknown")
    if platform not in {"instagram", "instagram_underscore", "tiktok"}:
        return {"applied": False, "platform": platform, "reason": "platform_not_targeted"}

    if not path.exists():
        raise RuntimeError(f"Vídeo final não encontrado: {path}")

    info = probe(path)
    duration = float(info["duration"])
    if duration <= 1.2:
        return {"applied": False, "platform": platform, "reason": "video_too_short"}

    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    stat = path.stat()
    base_seed = f"{platform}|{run_id}|{attempt}|{stat.st_size}|{duration:.3f}"

    zoom = choose(base_seed + "|zoom", [1.024, 1.030, 1.036, 1.043, 1.050])
    speed = choose(base_seed + "|speed", [0.978, 0.986, 0.993, 1.007, 1.015, 1.024, 1.032])
    x_bias = choose(base_seed + "|x", [-0.42, -0.22, 0.0, 0.22, 0.42])
    y_bias = choose(base_seed + "|y", [-0.30, -0.15, 0.0, 0.15, 0.30])
    contrast = choose(base_seed + "|contrast", [0.994, 1.000, 1.008, 1.014])
    saturation = choose(base_seed + "|sat", [0.990, 0.998, 1.008, 1.018])
    brightness = choose(base_seed + "|bright", [-0.006, -0.003, 0.0, 0.003, 0.006])

    max_start = min(0.72, max(0.10, duration * 0.055))
    max_end = min(0.52, max(0.08, duration * 0.040))
    start_ratio = choose(base_seed + "|start", [0.34, 0.48, 0.62, 0.78, 0.94])
    end_ratio = choose(base_seed + "|end", [0.30, 0.46, 0.64, 0.82, 0.96])
    trim_start = round(max_start * start_ratio, 3)
    trim_end = round(max_end * end_ratio, 3)
    trim_to = max(trim_start + 0.75, duration - trim_end)

    width = int(info["width"])
    height = int(info["height"])
    scaled_width = even(width * zoom)
    scaled_height = even(height * zoom)
    free_x = max(0, scaled_width - width)
    free_y = max(0, scaled_height - height)
    crop_x = int(round((free_x / 2) + x_bias * (free_x / 2)))
    crop_y = int(round((free_y / 2) + y_bias * (free_y / 2)))
    crop_x = max(0, min(crop_x, free_x))
    crop_y = max(0, min(crop_y, free_y))

    video_filter = (
        f"trim=start={trim_start}:end={trim_to},setpts=(PTS-STARTPTS)/{speed},"
        f"scale={scaled_width}:{scaled_height}:flags=lanczos,"
        f"crop={width}:{height}:{crop_x}:{crop_y},"
        f"eq=contrast={contrast}:brightness={brightness}:saturation={saturation},"
        "setsar=1[v]"
    )

    command = ["ffmpeg", "-y", "-i", str(path)]
    if info["has_audio"]:
        audio_filter = (
            f"atrim=start={trim_start}:end={trim_to},"
            f"asetpts=PTS-STARTPTS,atempo={speed}[a]"
        )
        command += [
            "-filter_complex", f"[0:v]{video_filter};[0:a]{audio_filter}",
            "-map", "[v]", "-map", "[a]",
        ]
    else:
        command += ["-filter_complex", f"[0:v]{video_filter}", "-map", "[v]"]

    maxrate = "14M" if width >= 1440 else "10M"
    bufsize = "28M" if width >= 1440 else "20M"
    command += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-maxrate", maxrate, "-bufsize", bufsize,
        "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
    ]
    if info["has_audio"]:
        command += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    command += ["-movflags", "+faststart", str(TEMP)]

    subprocess.run(command, check=True)
    TEMP.replace(path)

    report = {
        "applied": True,
        "platform": platform,
        "run_id": run_id,
        "run_attempt": attempt,
        "trim_start_seconds": trim_start,
        "trim_end_seconds": trim_end,
        "speed": speed,
        "zoom": zoom,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "contrast": contrast,
        "brightness": brightness,
        "saturation": saturation,
        "source_duration": duration,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "Variação exclusiva aplicada | "
        f"plataforma={platform} | corte={trim_start:.3f}s/{trim_end:.3f}s | "
        f"velocidade={speed:.3f}x | zoom={zoom:.3f}x | deslocamento={crop_x},{crop_y}"
    )
    return report


if __name__ == "__main__":
    differentiate()
