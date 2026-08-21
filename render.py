from __future__ import annotations
import json, os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "videos"
CONTENT = ROOT / "content.json"
STATE = ROOT / "state.json"
OUTDIR = ROOT / "output"
OUT = OUTDIR / "reel.mp4"
OVERLAY = OUTDIR / "overlay.png"
META = ROOT / "metadata.json"


def run(cmd):
    subprocess.run(cmd, check=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    raise RuntimeError("Nenhuma fonte compatível encontrada")


def fit_text(draw, text, max_width=930, max_lines=4):
    font_path = find_font()
    for size in range(72, 35, -2):
        font = ImageFont.truetype(font_path, size=size)
        words = text.strip().split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            box = draw.textbbox((0,0), test, font=font, stroke_width=4)
            if box[2] - box[0] <= max_width:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        if len(lines) <= max_lines:
            return font, lines
    return ImageFont.truetype(font_path, size=36), textwrap.wrap(text, width=28)[:max_lines]


def make_overlay(text):
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    font, lines = fit_text(draw, text)
    line_h = int(font.size * 1.22)
    total_h = line_h * len(lines)
    y = 250 - total_h // 2
    for line in lines:
        box = draw.textbbox((0,0), line, font=font, stroke_width=5)
        w = box[2]-box[0]
        x = (1080-w)//2
        draw.text((x,y), line, font=font, fill="white", stroke_width=5, stroke_fill="black", align="center")
        y += line_h
    img.save(OVERLAY)


def main():
    OUTDIR.mkdir(exist_ok=True)
    videos = sorted([p for p in VIDEOS.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}])
    if not videos:
        raise SystemExit("Nenhum vídeo encontrado na pasta videos/")
    content = load_json(CONTENT)
    if not content:
        raise SystemExit("content.json está vazio")
    state = load_json(STATE)
    vi = int(state.get("video_index", 0)) % len(videos)
    ci = int(state.get("content_index", 0)) % len(content)
    video = videos[vi]
    item = content[ci]
    overlay_text = str(item["overlay"]).strip()
    caption = str(item["caption"]).strip()
    make_overlay(overlay_text)

    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(OVERLAY),
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[base];[base][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
        "-r", "30", "-g", "60", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(OUT)
    ])

    next_state = {
        **state,
        "video_index": (vi + 1) % len(videos),
        "content_index": (ci + 1) % len(content),
        "posts_total": int(state.get("posts_total", 0)) + 1,
        "last_video": video.name,
        "last_overlay": overlay_text,
    }
    save_json(META, {
        "video": video.name,
        "overlay": overlay_text,
        "caption": caption,
        "next_state": next_state,
    })
    print(f"Renderizado: {video.name} | frase: {overlay_text}")

if __name__ == "__main__":
    main()
