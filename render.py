from __future__ import annotations
import json, os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "videos"
STATE = ROOT / "state.json"
PROFILES = ROOT / "video_profiles.json"
CONTENT = ROOT / "content.json"
OUTDIR = ROOT / "output"
OUT = OUTDIR / "reel.mp4"
OVERLAY = OUTDIR / "overlay.png"
META = ROOT / "metadata.json"
TARGET_W, TARGET_H = 1440, 2560


def run(cmd):
    subprocess.run(cmd, check=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_font():
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(p).exists():
            return p
    raise RuntimeError("Nenhuma fonte compatível encontrada")


def wrap_for_font(draw, text, font, max_width):
    words = text.strip().split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        box = draw.textbbox((0, 0), test, font=font)
        if box[2] - box[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, max_width=1220, max_lines=3):
    font_path = find_font()
    for size in range(72, 43, -2):
        font = ImageFont.truetype(font_path, size=size)
        lines = wrap_for_font(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = ImageFont.truetype(font_path, size=44)
    return font, textwrap.wrap(text, width=36)[:max_lines]


def make_overlay(text, theme):
    img = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font, lines = fit_text(draw, text)
    line_h = int(font.size * 1.25)
    box_x0, box_x1 = 55, TARGET_W - 55
    box_h = max(350, line_h * len(lines) + 100)
    y_by_theme = {
        "forro_antigo": 480,
        "brega": 610,
        "musica_terapia": 480,
        "generic": 500,
    }
    y0 = int(y_by_theme.get(theme, 500))
    y1 = y0 + box_h

    # Caixa opaca: substitui de fato a frase já gravada no arquivo.
    draw.rounded_rectangle(
        (box_x0, y0, box_x1, y1),
        radius=28,
        fill=(8, 8, 8, 255),
    )

    text_block_h = line_h * len(lines)
    y = y0 + (box_h - text_block_h) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        w = box[2] - box[0]
        x = (TARGET_W - w) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), align="center")
        y += line_h
    img.save(OVERLAY)


def choose_content(video_name, state):
    cfg = load_json(PROFILES)
    profile = cfg.get("profiles", {}).get(video_name, {})
    theme = profile.get("theme", "generic")
    pool = cfg.get("themes", {}).get(theme) or cfg.get("themes", {}).get("generic", [])
    if not pool:
        pool = load_json(CONTENT)
    usage = dict(state.get("variant_usage", {}))
    used = int(usage.get(video_name, 0))
    offset = int(profile.get("variant_offset", 0))
    idx = (used + offset) % len(pool)
    item = pool[idx]
    usage[video_name] = used + 1
    return item, theme, profile.get("source_text"), idx, usage


def main():
    OUTDIR.mkdir(exist_ok=True)
    videos = sorted([p for p in VIDEOS.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}])
    if not videos:
        raise SystemExit("Nenhum vídeo encontrado na pasta videos/")

    state = load_json(STATE)
    total_videos = max(1, int(os.environ.get("TOTAL_VIDEOS", len(videos))))
    current_video_index = int(state.get("video_index", 0)) % total_videos
    video = videos[0]
    item, theme, source_text, variant_idx, usage = choose_content(video.name, state)
    overlay_text = str(item["overlay"]).strip()
    caption = str(item["caption"]).strip()
    make_overlay(overlay_text, theme)

    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(OVERLAY),
        "-filter_complex",
        f"[0:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,crop={TARGET_W}:{TARGET_H},setsar=1[base];[base][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
        "-r", "30", "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(OUT),
    ])

    next_state = {
        **state,
        "video_index": (current_video_index + 1) % total_videos,
        "posts_total": int(state.get("posts_total", 0)) + 1,
        "last_video": video.name,
        "last_overlay": overlay_text,
        "variant_usage": usage,
    }
    save_json(META, {
        "video": video.name,
        "video_index": current_video_index,
        "total_videos": total_videos,
        "theme": theme,
        "source_text_detected": source_text,
        "variant_index": variant_idx,
        "overlay": overlay_text,
        "caption": caption,
        "render_resolution": f"{TARGET_W}x{TARGET_H}",
        "next_state": next_state,
    })
    print(f"Renderizado {video.name} | tema={theme} | variante={variant_idx + 1} | {TARGET_W}x{TARGET_H}")


if __name__ == "__main__":
    main()
