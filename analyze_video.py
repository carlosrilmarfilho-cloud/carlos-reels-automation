from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path

import cv2
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pytesseract import Output


ROOT = Path(__file__).resolve().parent
VIDEOS = Path(os.environ.get("VIDEOS_DIR", str(ROOT / "videos")))
OUT = ROOT / "video_analysis.json"

SAMPLE_RATIOS = (0.08, 0.20, 0.35, 0.50, 0.65, 0.80, 0.92)
EXPLICIT_TERMS = {
    "buceta", "caralho", "cu", "foder", "fode", "fudendo", "nude",
    "pau", "pica", "piroca", "putaria", "rola", "safada", "safado",
    "sexo", "sexual", "transar", "trepar",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def contains_explicit_terms(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", fold_text(text)))
    return bool(words & EXPLICIT_TERMS)


def safe_result(video_name: str, error: str = "") -> dict:
    result = {
        "video": video_name,
        "detected_text": "",
        "theme": "generic",
        "text_bbox_norm": None,
        "text_card_bbox_norm": None,
        "face_boxes_norm": [],
        "head_boxes_norm": [],
        "sample_times": [],
        "source_size": None,
        "explicit_source_text": False,
        "analysis_error": error[:500],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def video_duration(path: Path) -> float:
    process = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return max(0.1, float(process.stdout.strip()))
    except ValueError:
        return 1.0


def extract_frame(video: Path, second: float, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{second:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def preprocess(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(1.9)
    return gray.filter(ImageFilter.SHARPEN)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify(text: str) -> str:
    value = fold_text(text)
    if "brega" in value or "seresta" in value:
        return "brega"
    if any(term in value for term in ("forr", "sanfona", "zabumba", "vaquejada")):
        return "forro_antigo"
    if any(term in value for term in ("nordeste", "nordestino", "ceara", "paraiba", "pernambuco", "bahia", "maranhao")):
        return "nordeste_identidade"
    if "brasil" in value and any(term in value for term in ("dividir", "lado", "regiao", "terra")):
        return "nordeste_identidade"
    if any(term in value for term in ("irlanda", "europa", "imigrante", "exterior", "longe de casa", "morar fora")):
        return "brasileiro_exterior"
    if any(term in value for term in ("madrugada", "turno", "trabalho noturno", "fabrica")):
        return "trabalho_noturno"
    if any(term in value for term in ("vanlife", "motorhome", "camper", "minha van")):
        return "vanlife"
    if any(term in value for term in ("amor", "amar", "coracao", "romant")):
        return "romantica"
    if "terapia" in value or "musica" in value:
        return "musica_terapia"
    if any(term in value for term in ("saudade", "lembranca", "sofrer", "sofrimento")):
        return "saudade"
    return "generic"


def tesseract_data(processed: Image.Image) -> dict:
    last_error: Exception | None = None
    for language in ("por+eng", "eng"):
        try:
            return pytesseract.image_to_data(
                processed,
                lang=language,
                config="--psm 11",
                output_type=Output.DICT,
            )
        except Exception as exc:  # pragma: no cover - depends on runner language packs
            last_error = exc
    raise RuntimeError(f"OCR indisponível: {last_error}")


def line_candidates(path: Path) -> tuple[list[dict], tuple[int, int]]:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    data = tesseract_data(preprocess(image))
    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)

    for index, raw in enumerate(data.get("text", [])):
        word = normalize_text(raw)
        if not word:
            continue
        try:
            confidence = float(data["conf"][index])
        except (KeyError, TypeError, ValueError):
            confidence = -1
        if confidence < 40:
            continue
        x = int(data["left"][index])
        y = int(data["top"][index])
        box_width = int(data["width"][index])
        box_height = int(data["height"][index])
        if y > height * 0.72:
            continue
        key = (
            int(data.get("block_num", [0])[index]),
            int(data.get("par_num", [0])[index]),
            int(data.get("line_num", [0])[index]),
        )
        grouped[key].append(
            {
                "word": word,
                "confidence": confidence,
                "x0": x,
                "y0": y,
                "x1": x + box_width,
                "y1": y + box_height,
            }
        )

    candidates: list[dict] = []
    for words in grouped.values():
        text = normalize_text(" ".join(item["word"] for item in words))
        alphabetic = sum(char.isalpha() for char in text)
        if alphabetic < 8:
            continue
        confidence = sum(item["confidence"] for item in words) / len(words)
        x0 = min(item["x0"] for item in words)
        y0 = min(item["y0"] for item in words)
        x1 = max(item["x1"] for item in words)
        y1 = max(item["y1"] for item in words)
        width_ratio = (x1 - x0) / width
        height_ratio = (y1 - y0) / height
        if confidence < 55 or width_ratio < 0.18 or height_ratio > 0.12:
            continue
        bbox = {
            "x0": clamp(x0 / width),
            "y0": clamp(y0 / height),
            "x1": clamp(x1 / width),
            "y1": clamp(y1 / height),
        }
        score = alphabetic * confidence * (1.0 + width_ratio)
        candidates.append(
            {
                "text": text,
                "bbox": bbox,
                "confidence": confidence,
                "score": score,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates, (width, height)


def intersection_over_union(first: dict, second: dict) -> float:
    x0 = max(first["x0"], second["x0"])
    y0 = max(first["y0"], second["y0"])
    x1 = min(first["x1"], second["x1"])
    y1 = min(first["y1"], second["y1"])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    intersection = (x1 - x0) * (y1 - y0)
    first_area = (first["x1"] - first["x0"]) * (first["y1"] - first["y0"])
    second_area = (second["x1"] - second["x0"]) * (second["y1"] - second["y0"])
    return intersection / max(1e-9, first_area + second_area - intersection)


def dedupe_boxes(boxes: list[dict]) -> list[dict]:
    ordered = sorted(
        boxes,
        key=lambda box: (box["x1"] - box["x0"]) * (box["y1"] - box["y0"]),
        reverse=True,
    )
    kept: list[dict] = []
    for box in ordered:
        if all(intersection_over_union(box, existing) < 0.35 for existing in kept):
            kept.append(box)
    return kept


def face_and_head_boxes(path: Path) -> tuple[list[dict], list[dict]]:
    source = cv2.imread(str(path))
    if source is None:
        return [], []
    source_height, source_width = source.shape[:2]
    resize_scale = min(1.0, 960.0 / max(source_width, source_height))
    if resize_scale < 1.0:
        image = cv2.resize(
            source,
            (max(1, int(source_width * resize_scale)), max(1, int(source_height * resize_scale))),
            interpolation=cv2.INTER_AREA,
        )
    else:
        image = source
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cascades = [
        (cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"), False),
        (cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml"), False),
        (cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml"), True),
    ]
    detected: list[dict] = []
    min_side = max(36, int(min(image.shape[:2]) * 0.045))
    for cascade, mirror in cascades:
        scan = cv2.flip(gray, 1) if mirror else gray
        for x, y, width, height in cascade.detectMultiScale(
            scan,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(min_side, min_side),
        ):
            if mirror:
                x = image.shape[1] - x - width
            x0 = x / image.shape[1]
            y0 = y / image.shape[0]
            x1 = (x + width) / image.shape[1]
            y1 = (y + height) / image.shape[0]
            if (x1 - x0) < 0.055 or (y1 - y0) < 0.035:
                continue
            detected.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1})

    faces = dedupe_boxes(detected)
    heads: list[dict] = []
    for face in faces:
        width = face["x1"] - face["x0"]
        height = face["y1"] - face["y0"]
        heads.append(
            {
                "x0": clamp(face["x0"] - width * 0.18),
                "y0": clamp(face["y0"] - height * 0.23),
                "x1": clamp(face["x1"] + width * 0.18),
                "y1": clamp(face["y1"] + height * 0.18),
            }
        )
    return faces, heads


def detect_text_card_bbox(path: Path, text_bbox: dict | None) -> dict | None:
    """Find the compact light card behind the source text, including emoji tails."""
    if not text_bbox:
        return None
    image = cv2.imread(str(path))
    if image is None:
        return None
    height, width = image.shape[:2]
    roi_x0 = max(0, int((text_bbox["x0"] - 0.13) * width))
    roi_y0 = max(0, int((text_bbox["y0"] - 0.07) * height))
    roi_x1 = min(width, int((text_bbox["x1"] + 0.13) * width))
    roi_y1 = min(height, int((text_bbox["y1"] + 0.11) * height))
    if roi_x1 <= roi_x0 or roi_y1 <= roi_y0:
        return None

    roi = image[roi_y0:roi_y1, roi_x0:roi_x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 0, 205), (180, 75, 255))
    kernel_side = max(5, int(min(width, height) * 0.008))
    if kernel_side % 2 == 0:
        kernel_side += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_side, kernel_side))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)

    text_x0 = int(text_bbox["x0"] * width) - roi_x0
    text_y0 = int(text_bbox["y0"] * height) - roi_y0
    text_x1 = int(text_bbox["x1"] * width) - roi_x0
    text_y1 = int(text_bbox["y1"] * height) - roi_y0
    text_area = max(1, (text_x1 - text_x0) * (text_y1 - text_y0))
    candidates: list[tuple[float, dict]] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = (int(value) for value in stats[index])
        if (
            x <= 1
            or y <= 1
            or x + box_width >= roi.shape[1] - 1
            or y + box_height >= roi.shape[0] - 1
        ):
            continue
        global_x0, global_y0 = x + roi_x0, y + roi_y0
        global_x1, global_y1 = global_x0 + box_width, global_y0 + box_height
        width_ratio = box_width / width
        height_ratio = box_height / height
        if not (0.28 <= width_ratio <= 0.98 and 0.025 <= height_ratio <= 0.18):
            continue
        overlap_width = max(0, min(x + box_width, text_x1) - max(x, text_x0))
        overlap_height = max(0, min(y + box_height, text_y1) - max(y, text_y0))
        text_overlap = overlap_width * overlap_height / text_area
        if text_overlap < 0.45:
            continue
        candidate = {
            "x0": clamp((global_x0 - width * 0.004) / width),
            "y0": clamp((global_y0 - height * 0.004) / height),
            "x1": clamp((global_x1 + width * 0.004) / width),
            "y1": clamp((global_y1 + height * 0.004) / height),
        }
        candidates.append((text_overlap * area, candidate))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def aggregate_boxes(boxes: list[dict]) -> dict | None:
    if not boxes:
        return None
    middle = len(boxes) // 2
    return {
        key: sorted(float(box[key]) for box in boxes)[middle]
        for key in ("x0", "y0", "x1", "y1")
    }


def aggregate_text(candidates_by_frame: list[list[dict]]) -> tuple[str, dict | None]:
    best_per_frame = [candidates[0] for candidates in candidates_by_frame if candidates]
    if not best_per_frame:
        return "", None

    clusters: list[list[dict]] = []
    for candidate in best_per_frame:
        center = (candidate["bbox"]["y0"] + candidate["bbox"]["y1"]) / 2
        for cluster in clusters:
            existing = cluster[0]["bbox"]
            existing_center = (existing["y0"] + existing["y1"]) / 2
            if abs(center - existing_center) <= 0.075:
                cluster.append(candidate)
                break
        else:
            clusters.append([candidate])

    cluster = max(clusters, key=lambda group: (len(group), sum(item["score"] for item in group)))
    text_item = max(cluster, key=lambda item: (sum(char.isalpha() for char in item["text"]), item["score"]))
    ordered_x0 = sorted(item["bbox"]["x0"] for item in cluster)
    ordered_y0 = sorted(item["bbox"]["y0"] for item in cluster)
    ordered_x1 = sorted(item["bbox"]["x1"] for item in cluster)
    ordered_y1 = sorted(item["bbox"]["y1"] for item in cluster)
    middle = len(cluster) // 2
    bbox = {
        "x0": ordered_x0[middle],
        "y0": ordered_y0[middle],
        "x1": ordered_x1[middle],
        "y1": ordered_y1[middle],
    }
    return text_item["text"], bbox


def main() -> None:
    videos = [
        path for path in VIDEOS.iterdir()
        if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
    ]
    if not videos:
        raise SystemExit("Nenhum vídeo para analisar")
    video = videos[0]
    temporary_files: list[Path] = []
    try:
        duration = video_duration(video)
        sample_times = sorted(
            {
                round(min(max(0.15, duration * ratio), max(0.15, duration - 0.08)), 3)
                for ratio in SAMPLE_RATIOS
            }
        )
        candidates_by_frame: list[list[dict]] = []
        face_boxes: list[dict] = []
        head_boxes: list[dict] = []
        source_size: tuple[int, int] | None = None

        for number, second in enumerate(sample_times):
            frame = ROOT / f".analysis_frame_{number}.jpg"
            temporary_files.append(frame)
            extract_frame(video, second, frame)
            candidates, source_size = line_candidates(frame)
            candidates_by_frame.append(candidates)
            faces, heads = face_and_head_boxes(frame)
            for box in faces:
                face_boxes.append({**box, "sample_time": second})
            for box in heads:
                head_boxes.append({**box, "sample_time": second})

        detected_text, text_bbox = aggregate_text(candidates_by_frame)
        card_bbox = aggregate_boxes(
            [
                card
                for frame in temporary_files
                if (card := detect_text_card_bbox(frame, text_bbox)) is not None
            ]
        )
        result = {
            "video": video.name,
            "detected_text": detected_text,
            "theme": classify(detected_text),
            "text_bbox_norm": text_bbox,
            "text_card_bbox_norm": card_bbox,
            "face_boxes_norm": face_boxes,
            "head_boxes_norm": head_boxes,
            "sample_times": sample_times,
            "source_size": list(source_size) if source_size else None,
            "explicit_source_text": contains_explicit_terms(detected_text),
            "analysis_error": "",
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        result = safe_result(video.name, str(exc))
    finally:
        for path in temporary_files:
            path.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
