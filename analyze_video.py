from __future__ import annotations
import json, re, subprocess
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pytesseract import Output

ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "videos"
OUT = ROOT / "video_analysis.json"


def safe_result(video_name, error=""):
    result = {
        "video": video_name,
        "detected_text": "",
        "theme": "generic",
        "text_bbox_norm": None,
        "sample_time": 0,
        "source_size": None,
        "analysis_error": error[:500],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def video_duration(path: Path) -> float:
    p = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], check=True, capture_output=True, text=True)
    try:
        return max(0.1, float(p.stdout.strip()))
    except ValueError:
        return 1.0


def extract_frame(video: Path, second: float, out: Path):
    subprocess.run([
        "ffmpeg", "-y", "-ss", f"{second:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(out)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def preprocess(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    return gray.filter(ImageFilter.SHARPEN)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify(text: str) -> str:
    t = text.lower()
    if "brega" in t:
        return "brega"
    if "forró" in t or "forro" in t or "sanfona" in t or "zabumba" in t:
        return "forro_antigo"
    if "terapia" in t:
        return "musica_terapia"
    if any(k in t for k in ["saudade", "coração", "coracao", "amor", "amar", "sofrer", "sofrimento", "ex"]):
        return "generic"
    return "generic"


def tesseract_data(proc):
    # Português é preferido; se o pacote de idioma falhar, tenta inglês e depois cai para genérico.
    last_error = None
    for lang in ["por+eng", "eng"]:
        try:
            return pytesseract.image_to_data(proc, lang=lang, config="--psm 6", output_type=Output.DICT)
        except Exception as e:
            last_error = e
    raise RuntimeError(f"OCR indisponível: {last_error}")


def read_frame(path: Path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    proc = preprocess(img)
    data = tesseract_data(proc)
    words, boxes = [], []
    for i, raw in enumerate(data.get("text", [])):
        word = normalize_text(raw)
        if not word:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1
        if conf < 25:
            continue
        x, y = int(data["left"][i]), int(data["top"][i])
        bw, bh = int(data["width"][i]), int(data["height"][i])
        if y > h * 0.58:
            continue
        words.append(word)
        boxes.append((x, y, x + bw, y + bh))
    text = normalize_text(" ".join(words))
    bbox = None
    if boxes:
        x0 = max(0, min(b[0] for b in boxes))
        y0 = max(0, min(b[1] for b in boxes))
        x1 = min(w, max(b[2] for b in boxes))
        y1 = min(h, max(b[3] for b in boxes))
        bbox = {"x0": x0 / w, "y0": y0 / h, "x1": x1 / w, "y1": y1 / h}
    return text, bbox, (w, h)


def main():
    videos = [p for p in VIDEOS.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}]
    if not videos:
        raise SystemExit("Nenhum vídeo para analisar")
    video = videos[0]
    temp_files = []
    try:
        duration = video_duration(video)
        sample_times = sorted(set([min(0.7, duration * 0.15), min(1.8, duration * 0.35), min(3.0, duration * 0.55)]))
        candidates = []
        for n, sec in enumerate(sample_times):
            frame = ROOT / f".ocr_frame_{n}.jpg"
            temp_files.append(frame)
            extract_frame(video, sec, frame)
            text, bbox, size = read_frame(frame)
            candidates.append({"text": text, "bbox": bbox, "size": size, "time": sec})
        best = max(candidates, key=lambda x: len(x["text"])) if candidates else {"text": "", "bbox": None, "size": None, "time": 0}
        result = {
            "video": video.name,
            "detected_text": best["text"],
            "theme": classify(best["text"]),
            "text_bbox_norm": best["bbox"],
            "sample_time": best["time"],
            "source_size": best["size"],
            "analysis_error": "",
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        result = safe_result(video.name, str(e))
    finally:
        for p in temp_files:
            p.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
