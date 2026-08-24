from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import textwrap
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
VIDEOS = Path(os.environ.get("VIDEOS_DIR", str(ROOT / "videos")))
STATE = ROOT / "state.json"
PROFILES = ROOT / "video_profiles.json"
VIRAL_COPY = ROOT / "viral_copy.json"
ANALYSIS = ROOT / "video_analysis.json"
OUTDIR = ROOT / "output"
OUT = OUTDIR / "reel.mp4"
OVERLAY = OUTDIR / "overlay.png"
META = ROOT / "metadata.json"

EXPLICIT_TERMS = {
    "buceta", "caralho", "cu", "foder", "fode", "fudendo", "nude",
    "pau", "pica", "piroca", "putaria", "rola", "safada", "safado",
    "sexo", "sexual", "transar", "trepar",
}

COMMON_CAPTION_TEMPLATES = [
    "{ending}. Qual parte dessa história mais parece com a tua?",
    "{ending}. Você já viveu algo parecido?",
    "{ending}. Se isso também fala contigo, deixa uma palavra nos comentários.",
    "{ending}. Que lembrança essa ideia trouxe?",
    "{ending}. Salva para rever quando fizer sentido.",
    "{ending}. Quem entenderia isso sem você precisar explicar?",
    "{ending}. O que você acrescentaria a essa frase?",
    "{ending}. Concorda ou enxerga de outro jeito?",
    "{ending}. Em que momento isso ficou claro para você?",
    "{ending}. Qual pessoa veio à tua cabeça agora?",
    "{ending}. Essa também faz parte da tua história?",
    "{ending}. Se pudesse resumir em uma palavra, qual seria?",
]

HASHTAG_SETS = {
    "forro_antigo": [
        ["#forro", "#forrodasantigas", "#musicabrasileira", "#nordeste", "#reelsbrasil"],
        ["#forroantigo", "#forro", "#musicanordestina", "#nostalgia", "#reelsbrasil"],
        ["#forrodasantigas", "#musicaboa", "#sanfona", "#musicabrasileira", "#reelsbrasil"],
        ["#forro", "#classicosdoforro", "#forrozeiro", "#musicanordestina", "#reelsbrasil"],
    ],
    "brega": [
        ["#brega", "#musicabrega", "#musicabrasileira", "#nostalgia", "#reelsbrasil"],
        ["#bregadasantigas", "#brega", "#seresta", "#musicaboa", "#reelsbrasil"],
        ["#musicabrega", "#sofrencia", "#musicabrasileira", "#classicos", "#reelsbrasil"],
        ["#brega", "#seresta", "#nostalgia", "#musicabrasileira", "#reelsbrasil"],
    ],
    "romantica": [
        ["#musicaromantica", "#amor", "#musicabrasileira", "#sentimento", "#reelsbrasil"],
        ["#romantica", "#musica", "#saudade", "#musicaboa", "#reelsbrasil"],
        ["#canção", "#amor", "#musicabrasileira", "#reelsbrasil", "#boamusica"],
        ["#musicaromantica", "#relacionamento", "#sentimento", "#reelsbrasil", "#musica"],
    ],
    "saudade": [
        ["#saudade", "#musica", "#brasileiroseuropa", "#musicabrasileira", "#reelsbrasil"],
        ["#saudade", "#nostalgia", "#musicanordestina", "#reelsbrasil", "#musicaboa"],
        ["#brasileironoeexterior", "#saudade", "#musica", "#brasil", "#reelsbrasil"],
        ["#nostalgia", "#saudade", "#musicabrasileira", "#sentimento", "#reelsbrasil"],
    ],
    "nordeste_identidade": [
        ["#nordeste", "#nordestino", "#brasil", "#culturaNordestina", "#reelsbrasil"],
        ["#nordestino", "#orgulhonordestino", "#nordeste", "#brasileirosnomundo", "#reelsbrasil"],
        ["#nordeste", "#culturabrasileira", "#brasil", "#saudade", "#reelsbrasil"],
        ["#nordestinos", "#nordeste", "#brasileironaeuropa", "#brasil", "#reelsbrasil"],
    ],
    "brasileiro_exterior": [
        ["#brasileironaeuropa", "#brasileironairlanda", "#vidanoexterior", "#brasil", "#reelsbrasil"],
        ["#brasileirosnomundo", "#morarfora", "#saudade", "#europa", "#reelsbrasil"],
        ["#brasileironoexterior", "#irlanda", "#brasil", "#imigrante", "#reelsbrasil"],
        ["#vidanaeuropa", "#brasileironairlanda", "#saudade", "#brasileirosnomundo", "#reelsbrasil"],
    ],
    "trabalho_noturno": [
        ["#trabalhonoturno", "#turnodanoite", "#vidanotrabalho", "#brasileironaeuropa", "#reelsbrasil"],
        ["#madrugada", "#trabalho", "#rotinareal", "#irlanda", "#reelsbrasil"],
        ["#turnonoturno", "#vidareal", "#brasileironoexterior", "#trabalho", "#reelsbrasil"],
        ["#trabalhador", "#madrugada", "#rotina", "#europa", "#reelsbrasil"],
    ],
    "vanlife": [
        ["#vanlife", "#vanlifeeurope", "#campervan", "#vidanavan", "#reelsbrasil"],
        ["#vanlifeireland", "#motorhome", "#casasobrerodas", "#europa", "#reelsbrasil"],
        ["#vidanavan", "#camperlife", "#brasileironaeuropa", "#vanlife", "#reelsbrasil"],
        ["#campervan", "#vanlife", "#liberdade", "#irlanda", "#reelsbrasil"],
    ],
    "musica_terapia": [
        ["#musica", "#musicabrasileira", "#terapiamusical", "#musicaboa", "#reelsbrasil"],
        ["#musica", "#boamusica", "#sentimento", "#nostalgia", "#reelsbrasil"],
        ["#musicabrasileira", "#musica", "#som", "#reelsbrasil", "#musicaboa"],
        ["#boamusica", "#musica", "#sentimento", "#musicabrasileira", "#reelsbrasil"],
    ],
    "generic": [
        ["#musica", "#musicabrasileira", "#musicaboa", "#sentimento", "#reelsbrasil"],
        ["#musica", "#reelsbrasil", "#som", "#boamusica", "#brasil"],
        ["#musicabrasileira", "#reelsbrasil", "#musica", "#nostalgia", "#sentimento"],
        ["#boamusica", "#reelsbrasil", "#musica", "#brasil", "#reels"],
    ],
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def contains_explicit_terms(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", fold_text(text)))
    return bool(words & EXPLICIT_TERMS)


def caption_signature(text: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    tail = sentences[-1] if sentences else text.strip()
    return fold_text(tail).strip(" .!?")


def validate_copy(overlay: str, caption: str) -> None:
    if contains_explicit_terms(f"{overlay} {caption}"):
        raise RuntimeError("Conteúdo bloqueado pelo filtro de linguagem sexual")
    if not 16 <= len(overlay) <= 82:
        raise RuntimeError(f"Frase fora do tamanho editorial seguro: {len(overlay)} caracteres")
    if not 20 <= len(caption) <= 220:
        raise RuntimeError(f"Legenda fora do tamanho editorial seguro: {len(caption)} caracteres")


def probe_size(video: Path) -> tuple[int, int]:
    process = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(process.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def target_size(video: Path) -> tuple[int, int]:
    source_width, source_height = probe_size(video)
    if source_width >= 1440 and source_height >= 2560:
        return 1440, 2560
    return 1080, 1920


def find_font() -> str:
    for path in (
        "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return path
    raise RuntimeError("Nenhuma fonte compatível encontrada")


def wrap_for_font(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    target_width: int,
    max_lines: int = 2,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    font_path = find_font()
    scale = target_width / 1080
    start_size = max(44, int(58 * scale))
    minimum_size = max(30, int(36 * scale))
    for size in range(start_size, minimum_size - 1, -2):
        font = ImageFont.truetype(font_path, size=size)
        lines = wrap_for_font(draw, text, font, max_width)
        if len(lines) <= max_lines:
            line_height = int(font.size * 1.18)
            return font, lines, line_height
    font = ImageFont.truetype(font_path, size=minimum_size)
    lines = textwrap.wrap(text, width=34)
    if len(lines) > max_lines:
        raise RuntimeError("Frase não cabe em duas linhas sem cobrir a imagem")
    return font, lines, int(font.size * 1.18)


def rendering_geometry(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> tuple[float, float, float]:
    scale = min(target_width / source_width, target_height / source_height)
    offset_x = (target_width - source_width * scale) / 2
    offset_y = (target_height - source_height * scale) / 2
    return scale, offset_x, offset_y


def map_norm_box(
    box: dict,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> dict:
    scale, offset_x, offset_y = rendering_geometry(
        source_width,
        source_height,
        target_width,
        target_height,
    )
    return {
        "x0": offset_x + float(box["x0"]) * source_width * scale,
        "y0": offset_y + float(box["y0"]) * source_height * scale,
        "x1": offset_x + float(box["x1"]) * source_width * scale,
        "y1": offset_y + float(box["y1"]) * source_height * scale,
    }


def boxes_intersect(first: dict, second: dict, margin: float = 0.0) -> bool:
    return not (
        first["x1"] + margin <= second["x0"]
        or first["x0"] - margin >= second["x1"]
        or first["y1"] + margin <= second["y0"]
        or first["y0"] - margin >= second["y1"]
    )


def overlap_fraction(first: dict, second: dict) -> float:
    x0 = max(first["x0"], second["x0"])
    y0 = max(first["y0"], second["y0"])
    x1 = min(first["x1"], second["x1"])
    y1 = min(first["y1"], second["y1"])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    intersection = (x1 - x0) * (y1 - y0)
    first_area = max(1.0, (first["x1"] - first["x0"]) * (first["y1"] - first["y0"]))
    return intersection / first_area


def normalized_rect(rect: dict, width: int, height: int) -> dict:
    return {
        "x0": rect["x0"] / width,
        "y0": rect["y0"] / height,
        "x1": rect["x1"] / width,
        "y1": rect["y1"] / height,
    }


def plan_overlay(
    draw: ImageDraw.ImageDraw,
    text: str,
    analysis: dict,
    source_size: tuple[int, int],
    target_size_value: tuple[int, int],
) -> tuple[ImageFont.FreeTypeFont, list[str], int, dict, list[dict]]:
    source_width, source_height = source_size
    target_width, target_height = target_size_value
    scale = target_width / 1080
    side_margin = int(target_width * 0.045)
    horizontal_padding = int(26 * scale)
    vertical_padding = int(20 * scale)
    text_bbox = analysis.get("text_bbox_norm")
    text_card_bbox = analysis.get("text_card_bbox_norm")
    source_box_norm = text_card_bbox or text_bbox
    has_detected_card = bool(text_card_bbox)
    mapped_faces = [
        map_norm_box(box, source_width, source_height, target_width, target_height)
        for box in analysis.get("face_boxes_norm", [])
    ]
    mapped_heads = [
        map_norm_box(box, source_width, source_height, target_width, target_height)
        for box in analysis.get("head_boxes_norm", [])
    ]

    if source_box_norm:
        source_rect = map_norm_box(source_box_norm, source_width, source_height, target_width, target_height)
        left_padding_ratio = 0.008 if has_detected_card else 0.055
        right_padding_ratio = 0.008 if has_detected_card else 0.12
        x0 = max(side_margin, source_rect["x0"] - target_width * left_padding_ratio)
        x1 = min(target_width - side_margin, source_rect["x1"] + target_width * right_padding_ratio)
        minimum_width = target_width * 0.76
        if x1 - x0 < minimum_width:
            center = (x0 + x1) / 2
            x0 = max(side_margin, center - minimum_width / 2)
            x1 = min(target_width - side_margin, x0 + minimum_width)
            x0 = max(side_margin, x1 - minimum_width)
    else:
        source_rect = None
        x0, x1 = side_margin, target_width - side_margin

    font, lines, line_height = fit_text(
        draw,
        text,
        int(x1 - x0) - horizontal_padding * 2,
        target_width,
    )
    box_height = line_height * len(lines) + vertical_padding * 2
    if box_height > target_height * 0.145:
        raise RuntimeError("Caixa de texto excederia o limite visual seguro")

    candidates: list[dict] = []
    if source_rect:
        if has_detected_card:
            cover_top = source_rect["y0"]
            cover_bottom = source_rect["y1"]
        else:
            cover_top = source_rect["y0"] - target_height * 0.018
            # Sem cartão detectável, aplica uma folga limitada ao redor do OCR.
            bottom_padding_ratio = 0.038 if source_rect["y0"] < target_height * 0.21 else 0.022
            cover_bottom = source_rect["y1"] + target_height * bottom_padding_ratio
        box_height = max(box_height, cover_bottom - cover_top)
        if box_height > target_height * 0.145:
            raise RuntimeError("Área original de texto é grande demais para uma substituição segura")
        candidates.extend(
            [
                {"x0": x0, "y0": cover_bottom - box_height, "x1": x1, "y1": cover_bottom},
                {"x0": x0, "y0": cover_top, "x1": x1, "y1": cover_top + box_height},
                {
                    "x0": x0,
                    "y0": (cover_top + cover_bottom - box_height) / 2,
                    "x1": x1,
                    "y1": (cover_top + cover_bottom + box_height) / 2,
                },
            ]
        )
        obstacles = mapped_faces
    else:
        safe_centers = (0.13, 0.25, 0.68, 0.78)
        for center_ratio in safe_centers:
            center_y = target_height * center_ratio
            candidates.append(
                {
                    "x0": x0,
                    "y0": center_y - box_height / 2,
                    "x1": x1,
                    "y1": center_y + box_height / 2,
                }
            )
        obstacles = mapped_heads or mapped_faces

    top_limit = target_height * 0.045
    bottom_limit = target_height * 0.84
    chosen = None
    for candidate in candidates:
        if candidate["y0"] < top_limit or candidate["y1"] > bottom_limit:
            continue
        if source_rect and not (
            candidate["y0"] <= source_rect["y0"]
            and candidate["y1"] >= source_rect["y1"]
        ):
            continue
        # Tolera apenas um toque mínimo de borda causado pela imprecisão do detector.
        # Uma caixa atravessando rosto/cabeça continua sendo bloqueada com folga.
        if any(overlap_fraction(candidate, obstacle) > 0.035 for obstacle in obstacles):
            continue
        chosen = candidate
        break

    if chosen is None:
        raise RuntimeError("Nenhuma área livre permite trocar o texto sem cobrir o rosto")

    chosen = {key: int(round(value)) for key, value in chosen.items()}
    return font, lines, line_height, chosen, mapped_faces


def make_overlay(
    text: str,
    analysis: dict,
    source_size: tuple[int, int],
    target_size_value: tuple[int, int],
) -> tuple[dict, list[dict]]:
    target_width, target_height = target_size_value
    image = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font, lines, line_height, rect, mapped_faces = plan_overlay(
        draw,
        text,
        analysis,
        source_size,
        target_size_value,
    )
    scale = target_width / 1080
    radius = max(16, int(22 * scale))
    shadow_offset = max(3, int(5 * scale))
    draw.rounded_rectangle(
        (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),
        radius=radius,
        fill=(0, 0, 0, 52),
    )
    draw.rounded_rectangle(
        (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),
        radius=radius,
        fill=(250, 250, 250, 255),
        outline=(232, 232, 232, 255),
        width=max(1, int(2 * scale)),
    )

    text_height = line_height * len(lines)
    y = rect["y0"] + max(0, (rect["y1"] - rect["y0"] - text_height) // 2)
    for line in lines:
        text_box = draw.textbbox((0, 0), line, font=font)
        text_width = text_box[2] - text_box[0]
        x = (target_width - text_width) // 2
        draw.text((x, y), line, font=font, fill=(18, 18, 18, 255), align="center")
        y += line_height
    image.save(OVERLAY)
    return rect, mapped_faces


def expand_variants(section: dict, key: str) -> list[str]:
    direct = [str(value).strip() for value in section.get(key, []) if str(value).strip()]
    templates = list(section.get(f"{key}_templates", []))
    endings = section.get(f"{key}_endings", [])
    for template in templates:
        for ending in endings:
            direct.append(str(template).format(ending=str(ending)).strip())
    unique: list[str] = []
    seen: set[str] = set()
    for value in direct:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def deterministic_index(seed_text: str, length: int) -> int:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % max(1, length)


def choose_unused(values: list[str], used: set[str], seed_text: str) -> tuple[str, int]:
    if not values:
        raise RuntimeError("Banco editorial vazio")
    start = deterministic_index(seed_text, len(values))
    for step in range(len(values)):
        index = (start + step * 17) % len(values)
        value = values[index]
        if value not in used and not contains_explicit_terms(value):
            return value, index
    raise RuntimeError("Banco editorial esgotado; repetição foi bloqueada")


def choose_content(video_name: str, state: dict, analysis: dict) -> tuple[dict, str, str, int, dict]:
    profiles = load_json(PROFILES, {})
    copy_bank = load_json(VIRAL_COPY, {})
    profile = profiles.get("profiles", {}).get(video_name, {})
    analyzed_theme = str(analysis.get("theme", "generic"))
    theme = str(profile.get("theme") or analyzed_theme)
    section = copy_bank.get(theme) or copy_bank.get("generic", {})
    overlays = expand_variants(section, "overlays")
    captions = expand_variants(section, "captions")
    used_overlays = set(state.get("recent_overlays", []))
    recent_caption_values = list(state.get("recent_captions", []))
    used_captions = set(recent_caption_values)
    recent_caption_signatures = {
        caption_signature(value) for value in recent_caption_values[-12:]
    }
    captions = [
        value for value in captions
        if caption_signature(value) not in recent_caption_signatures
    ]
    post_number = int(state.get("posts_total", 0))
    overlay, overlay_index = choose_unused(
        overlays,
        used_overlays,
        f"overlay|{video_name}|{theme}|{post_number}",
    )
    caption, _ = choose_unused(
        captions,
        used_captions,
        f"caption|{theme}|{video_name}|{post_number}|{overlay_index}",
    )
    validate_copy(overlay, caption)
    source_text = str(profile.get("source_text") or analysis.get("detected_text") or "")
    usage = dict(state.get("variant_usage", {}))
    usage[video_name] = int(usage.get(video_name, 0)) + 1
    return {"overlay": overlay, "caption": caption}, theme, source_text, overlay_index, usage


def choose_hashtags(theme: str, state: dict, variant_index: int) -> str:
    sets = HASHTAG_SETS.get(theme) or HASHTAG_SETS["generic"]
    index = (int(state.get("posts_total", 0)) + int(variant_index)) % len(sets)
    return " ".join(sets[index])


def main() -> None:
    OUTDIR.mkdir(exist_ok=True)
    videos = sorted(
        path for path in VIDEOS.iterdir()
        if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
    )
    if not videos:
        raise SystemExit("Nenhum vídeo encontrado na pasta videos/")

    state = load_json(STATE, {})
    analysis = load_json(ANALYSIS, {})
    if analysis.get("analysis_error"):
        raise RuntimeError(f"Análise visual incompleta: {analysis['analysis_error']}")
    if analysis.get("explicit_source_text"):
        raise RuntimeError("Vídeo bloqueado: texto sexual detectado na origem")

    total_videos = max(1, int(os.environ.get("TOTAL_VIDEOS", len(videos))))
    current_video_index = int(state.get("video_index", 0)) % total_videos
    video = videos[0]
    source_width, source_height = probe_size(video)
    target_width, target_height = target_size(video)
    item, theme, source_text, variant_index, usage = choose_content(video.name, state, analysis)
    overlay_text = item["overlay"].strip()
    base_caption = item["caption"].strip()
    hashtags = choose_hashtags(theme, state, variant_index)
    caption = f"{base_caption}\n\n{hashtags}".strip()

    try:
        overlay_rect, mapped_faces = make_overlay(
            overlay_text,
            analysis,
            (source_width, source_height),
            (target_width, target_height),
        )
    except RuntimeError as exc:
        if str(exc) == "Nenhuma área livre permite trocar o texto sem cobrir o rosto":
            blocked = list(dict.fromkeys(list(state.get("blocked_videos", [])) + [video.name]))
            state["blocked_videos"] = blocked
            state["video_index"] = (current_video_index + 1) % total_videos
            save_json(STATE, state)
        raise

    maxrate = "14M" if target_width >= 1440 else "10M"
    bufsize = "28M" if target_width >= 1440 else "20M"
    run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(OVERLAY),
            "-filter_complex",
            (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[base];"
                "[base][1:v]overlay=0:0[v]"
            ),
            "-map", "[v]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-maxrate", maxrate, "-bufsize", bufsize, "-pix_fmt", "yuv420p",
            "-r", "30", "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-shortest", str(OUT),
        ]
    )

    recent_overlays = (list(state.get("recent_overlays", [])) + [overlay_text])[-480:]
    recent_captions = (list(state.get("recent_captions", [])) + [base_caption])[-480:]
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
    save_json(
        META,
        {
            "video": video.name,
            "video_index": current_video_index,
            "total_videos": total_videos,
            "theme": theme,
            "source_text_detected": source_text,
            "automatic_analysis": True,
            "variant_index": variant_index,
            "overlay": overlay_text,
            "caption": caption,
            "hashtags": hashtags,
            "source_resolution": f"{source_width}x{source_height}",
            "render_resolution": f"{target_width}x{target_height}",
            "overlay_rect_px": overlay_rect,
            "overlay_rect_norm": normalized_rect(overlay_rect, target_width, target_height),
            "face_boxes_mapped_px": mapped_faces,
            "visual_rules": {
                "preserve_full_frame": True,
                "maximum_overlay_height_ratio": 0.145,
                "face_overlap_allowed": False,
                "explicit_language_allowed": False,
            },
            "next_state": next_state,
        },
    )
    print(
        f"Renderizado {video.name} | tema={theme} | variante={variant_index + 1} | "
        f"{target_width}x{target_height} | rosto livre | enquadramento preservado"
    )


if __name__ == "__main__":
    main()
