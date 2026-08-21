from __future__ import annotations
import json, os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "videos"
STATE = ROOT / "state.json"
PROFILES = ROOT / "video_profiles.json"
CONTENT = ROOT / "content.json"
ANALYSIS = ROOT / "video_analysis.json"
OUTDIR = ROOT / "output"
OUT = OUTDIR / "reel.mp4"
OVERLAY = OUTDIR / "overlay.png"
META = ROOT / "metadata.json"

HASHTAG_SETS = {
    "forro_antigo": [
        ["#forro", "#forrodasantigas", "#musicabrasileira", "#reelsbrasil", "#forrozeiro"],
        ["#forroantigo", "#forro", "#musicanordestina", "#nostalgia", "#reelsbrasil"],
        ["#forrodasantigas", "#musicaboa", "#nordeste", "#musicabrasileira", "#reelsbrasil"],
        ["#forro", "#classicosdoforro", "#sanfona", "#musicanordestina", "#reelsbrasil"],
    ],
    "brega": [
        ["#brega", "#musicabrega", "#musicabrasileira", "#reelsbrasil", "#nostalgia"],
        ["#bregadasantigas", "#brega", "#seresta", "#musicaboa", "#reelsbrasil"],
        ["#musicabrega", "#sofrencia", "#musicabrasileira", "#nostalgia", "#reelsbrasil"],
        ["#brega", "#seresta", "#classicos", "#musicabrasileira", "#reelsbrasil"],
    ],
    "musica_terapia": [
        ["#musica", "#musicabrasileira", "#reelsbrasil", "#nostalgia", "#boamusica"],
        ["#musica", "#terapiamusical", "#musicaboa", "#reelsbrasil", "#sentimento"],
        ["#musicabrasileira", "#musica", "#reelsbrasil", "#som", "#nostalgia"],
        ["#boamusica", "#musica", "#sentimento", "#musicabrasileira", "#reelsbrasil"],
    ],
    "generic": [
        ["#musica", "#musicabrasileira", "#reelsbrasil", "#musicaboa"],
        ["#musica", "#reelsbrasil", "#som", "#sentimento"],
        ["#musicabrasileira", "#reelsbrasil", "#musica", "#nostalgia"],
        ["#boamusica", "#reelsbrasil", "#musica", "#brasil"],
    ],
}


def run(cmd):
    subprocess.run(cmd, check=True)


def load_json(path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe_size(video):
    p = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(video)
    ], check=True, capture_output=True, text=True)
    s = json.loads(p.stdout)["streams"][0]
    return int(s["width"]), int(s["height"])


def target_size(video):
    sw, sh = probe_size(video)
    # Preserva detalhe real; não cria upscale falso. Cap em 1440x2560 para estabilidade da API.
    if sw >= 1440 and sh >= 2560:
        return 1440, 2560
    return 1080, 1920


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


def fit_text(draw, text, width, max_lines=3):
    font_path = find_font()
    scale = width / 1440
    max_width = int(1220 * scale)
    start_size = max(52, int(72 * scale))
    min_size = max(34, int(44 * scale))
    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size=size)
        lines = wrap_for_font(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = ImageFont.truetype(font_path, size=min_size)
    return font, textwrap.wrap(text, width=36)[:max_lines]


def make_overlay(text, theme, width, height, dynamic_bbox=None):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font, lines = fit_text(draw, text, width)
    scale = width / 1440
    line_h = int(font.size * 1.25)
    margin = int(55 * scale)
    box_x0, box_x1 = margin, width - margin
    min_box_h = max(int(350 * scale), line_h * len(lines) + int(100 * scale))

    if dynamic_bbox:
        # Para vídeos novos: usa a região de texto detectada automaticamente e dá folga ao redor.
        y0 = max(int(height * dynamic_bbox.get("y0", 0.18)) - int(70 * scale), int(40 * scale))
        detected_y1 = min(int(height * dynamic_bbox.get("y1", 0.34)) + int(70 * scale), height - int(40 * scale))
        box_h = max(min_box_h, detected_y1 - y0)
    else:
        y_ratio = {
            "forro_antigo": 480 / 2560,
            "brega": 610 / 2560,
            "musica_terapia": 480 / 2560,
            "generic": 500 / 2560,
        }
        y0 = int(height * y_ratio.get(theme, 500 / 2560))
        box_h = min_box_h

    y1 = min(height - int(40 * scale), y0 + box_h)
    draw.rounded_rectangle(
        (box_x0, y0, box_x1, y1),
        radius=max(18, int(28 * scale)),
        fill=(8, 8, 8, 255),
    )
    text_block_h = line_h * len(lines)
    y = y0 + max(0, (y1 - y0 - text_block_h) // 2)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        w = box[2] - box[0]
        x = (width - w) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), align="center")
        y += line_h
    img.save(OVERLAY)


def choose_content(video_name, state, analysis):
    cfg = load_json(PROFILES, {})
    profile = cfg.get("profiles", {}).get(video_name, {})
    analyzed_theme = str(analysis.get("theme", "generic"))
    theme = profile.get("theme") or analyzed_theme
    pool = cfg.get("themes", {}).get(theme) or cfg.get("themes", {}).get("generic", [])
    if not pool:
        pool = load_json(CONTENT, [])
    if not pool:
        raise RuntimeError("Nenhuma frase disponível")

    usage = dict(state.get("variant_usage", {}))
    used = int(usage.get(video_name, 0))
    offset = int(profile.get("variant_offset", 0))
    recent = set(state.get("recent_overlays", [])[-14:])

    chosen_idx = (used + offset) % len(pool)
    for step in range(len(pool)):
        idx = (used + offset + step) % len(pool)
        if str(pool[idx].get("overlay", "")) not in recent:
            chosen_idx = idx
            break

    item = pool[chosen_idx]
    usage[video_name] = used + 1
    source_text = profile.get("source_text") or analysis.get("detected_text") or ""
    return item, theme, source_text, chosen_idx, usage, bool(profile)


def choose_hashtags(theme, state, variant_idx):
    sets = HASHTAG_SETS.get(theme) or HASHTAG_SETS["generic"]
    idx = (int(state.get("posts_total", 0)) + int(variant_idx)) % len(sets)
    return " ".join(sets[idx])


def main():
    OUTDIR.mkdir(exist_ok=True)
    videos = sorted([p for p in VIDEOS.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}])
    if not videos:
        raise SystemExit("Nenhum vídeo encontrado na pasta videos/")

    state = load_json(STATE, {})
    analysis = load_json(ANALYSIS, {})
    total_videos = max(1, int(os.environ.get("TOTAL_VIDEOS", len(videos))))
    current_video_index = int(state.get("video_index", 0)) % total_videos
    video = videos[0]
    target_w, target_h = target_size(video)
    item, theme, source_text, variant_idx, usage, has_manual_profile = choose_content(video.name, state, analysis)
    overlay_text = str(item["overlay"]).strip()
    base_caption = str(item["caption"]).strip()
    hashtags = choose_hashtags(theme, state, variant_idx)
    caption = f"{base_caption}\n\n{hashtags}".strip()

    dynamic_bbox = None if has_manual_profile else analysis.get("text_bbox_norm")
    make_overlay(overlay_text, theme, target_w, target_h, dynamic_bbox=dynamic_bbox)

    maxrate = "14M" if target_w >= 1440 else "10M"
    bufsize = "28M" if target_w >= 1440 else "20M"
    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(OVERLAY),
        "-filter_complex",
        f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},setsar=1[base];[base][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", maxrate, "-bufsize", bufsize, "-pix_fmt", "yuv420p",
        "-r", "30", "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(OUT),
    ])

    recent_overlays = (list(state.get("recent_overlays", [])) + [overlay_text])[-18:]
    recent_captions = (list(state.get("recent_captions", [])) + [base_caption])[-18:]
    next_state = {
        **state,
        "video_index": (current_video_index + 1) % total_videos,
        "posts_total": int(state.get("posts_total", 0)) + 1,
        "last_video": video.name,
        "last_overlay": overlay_text,
        "last_caption": base_caption,
        "last_hashtags": hashtags,
        "variant_usage": usage,
        "recent_overlays": recent_overlays,
        "recent_captions": recent_captions,
    }
    save_json(META, {
        "video": video.name,
        "video_index": current_video_index,
        "total_videos": total_videos,
        "theme": theme,
        "source_text_detected": source_text,
        "automatic_analysis": not has_manual_profile,
        "variant_index": variant_idx,
        "overlay": overlay_text,
        "caption": caption,
        "hashtags": hashtags,
        "render_resolution": f"{target_w}x{target_h}",
        "next_state": next_state,
    })
    print(f"Renderizado {video.name} | tema={theme} | variante={variant_idx + 1} | {target_w}x{target_h} | hashtags rotativas")


if __name__ == "__main__":
    main()
