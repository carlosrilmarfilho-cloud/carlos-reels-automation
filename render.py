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


def fit_text(draw, text, max_width, canvas_width, max_lines=3):
    font_path = find_font()
    scale = canvas_width / 1440
    start_size = max(46, int(64 * scale))
    min_size = max(32, int(40 * scale))
    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size=size)
        lines = wrap_for_font(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = ImageFont.truetype(font_path, size=min_size)
    return font, textwrap.wrap(text, width=36)[:max_lines]


def normalized_box(raw):
    if not isinstance(raw, dict):
        return None
    try:
        x0 = float(raw["x0"])
        y0 = float(raw["y0"])
        x1 = float(raw["x1"])
        y1 = float(raw["y1"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0.03 <= x0 < x1 <= 0.97 and 0.04 <= y0 < y1 <= 0.86):
        return None
    if x1 - x0 > 0.88 or y1 - y0 > 0.18:
        return None
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def make_overlay(text, width, height, safe_text_box=None):
    """Desenha somente texto compacto em uma área humana/revisada.

    Sem uma área segura explícita, o overlay fica transparente e o gancho é
    transferido para a legenda. Isso é intencional: nunca arriscar cobrir rosto,
    cabeça ou sujeito principal.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    safe = normalized_box(safe_text_box)
    if not safe:
        img.save(OVERLAY)
        return {
            "applied": False,
            "reason": "sem_area_livre_revisada",
            "text_bbox_norm": None,
        }

    scale = width / 1440
    x0 = int(width * safe["x0"])
    y0 = int(height * safe["y0"])
    x1 = int(width * safe["x1"])
    y1 = int(height * safe["y1"])
    padding = max(12, int(22 * scale))
    max_width = max(120, x1 - x0 - 2 * padding)
    font, lines = fit_text(draw, text, max_width, width, max_lines=3)
    line_h = int(font.size * 1.25)
    text_block_h = line_h * len(lines)
    if text_block_h > y1 - y0 - 2 * padding:
        img.save(OVERLAY)
        return {
            "applied": False,
            "reason": "texto_nao_cabe_na_area_segura",
            "text_bbox_norm": None,
        }

    y = y0 + max(padding, (y1 - y0 - text_block_h) // 2)
    drawn = []
    stroke = max(2, int(5 * scale))
    shadow = max(2, int(4 * scale))
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        w = box[2] - box[0]
        x = x0 + (x1 - x0 - w) // 2
        if x < x0 + padding or x + w > x1 - padding:
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            img.save(OVERLAY)
            return {
                "applied": False,
                "reason": "texto_excede_area_segura",
                "text_bbox_norm": None,
            }
        draw.text(
            (x + shadow, y + shadow),
            line,
            font=font,
            fill=(0, 0, 0, 170),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 170),
            align="center",
        )
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 220),
            align="center",
        )
        drawn.append((x, y, x + w, y + line_h))
        y += line_h
    img.save(OVERLAY)
    bx0 = min(b[0] for b in drawn)
    by0 = min(b[1] for b in drawn)
    bx1 = max(b[2] for b in drawn)
    by1 = max(b[3] for b in drawn)
    return {
        "applied": True,
        "reason": "area_livre_revisada",
        "text_bbox_norm": {
            "x0": bx0 / width,
            "y0": by0 / height,
            "x1": bx1 / width,
            "y1": by1 / height,
        },
    }


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
    return item, theme, source_text, chosen_idx, usage, profile


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
    item, theme, source_text, variant_idx, usage, profile = choose_content(video.name, state, analysis)
    overlay_text = str(item["overlay"]).strip()
    base_caption = str(item["caption"]).strip()
    hashtags = choose_hashtags(theme, state, variant_idx)
    overlay_result = make_overlay(
        overlay_text,
        target_w,
        target_h,
        safe_text_box=profile.get("safe_text_box"),
    )
    if overlay_result["applied"]:
        caption = f"{base_caption}\n\n{hashtags}".strip()
    else:
        caption = f"{overlay_text}\n\n{base_caption}\n\n{hashtags}".strip()

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
        "automatic_analysis": not bool(profile),
        "variant_index": variant_idx,
        "overlay": overlay_text,
        "overlay_applied": overlay_result["applied"],
        "overlay_reason": overlay_result["reason"],
        "overlay_text_bbox_norm": overlay_result["text_bbox_norm"],
        "safe_text_box": normalized_box(profile.get("safe_text_box")),
        "visual_policy": "sem_caixa_preta_e_sem_sobrepor_rosto",
        "caption": caption,
        "hashtags": hashtags,
        "render_resolution": f"{target_w}x{target_h}",
        "next_state": next_state,
    })
    print(f"Renderizado {video.name} | tema={theme} | variante={variant_idx + 1} | {target_w}x{target_h} | hashtags rotativas")


if __name__ == "__main__":
    main()
