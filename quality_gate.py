from __future__ import annotations

import json
import subprocess
from pathlib import Path

from analyze_video import face_and_head_boxes, video_duration
from render import contains_explicit_terms, load_json, overlap_fraction


ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "output" / "reel.mp4"
META = ROOT / "metadata.json"
REPORT = ROOT / "quality-report.json"


def extract_frame(second: float, path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{second:.3f}", "-i", str(VIDEO),
            "-frames:v", "1", "-q:v", "2", str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def validate_rect(rect: dict) -> list[str]:
    failures: list[str] = []
    width = float(rect["x1"]) - float(rect["x0"])
    height = float(rect["y1"]) - float(rect["y0"])
    if width <= 0 or height <= 0:
        failures.append("caixa de texto inválida")
    if height > 0.145:
        failures.append(f"caixa alta demais ({height:.3f})")
    if width * height > 0.14:
        failures.append(f"caixa ocupa área excessiva ({width * height:.3f})")
    if float(rect["y0"]) < 0.04 or float(rect["y1"]) > 0.84:
        failures.append("caixa fora da área segura do Reel")
    return failures


def main() -> None:
    metadata = load_json(META, {})
    failures: list[str] = []
    overlay_rect = metadata.get("overlay_rect_norm")
    if not overlay_rect:
        failures.append("posição do texto ausente")
    else:
        failures.extend(validate_rect(overlay_rect))

    copy = f"{metadata.get('overlay', '')} {metadata.get('caption', '')}"
    if contains_explicit_terms(copy):
        failures.append("linguagem sexual detectada")
    if not metadata.get("visual_rules", {}).get("preserve_full_frame"):
        failures.append("preservação do enquadramento não confirmada")

    detected_faces: list[dict] = []
    temporary_files: list[Path] = []
    try:
        duration = video_duration(VIDEO)
        sample_times = sorted(
            {
                round(min(max(0.15, duration * ratio), max(0.15, duration - 0.08)), 3)
                for ratio in (0.08, 0.20, 0.35, 0.50, 0.65, 0.80, 0.92)
            }
        )
        for index, second in enumerate(sample_times):
            frame = ROOT / f".quality_frame_{index}.jpg"
            temporary_files.append(frame)
            extract_frame(second, frame)
            faces, _ = face_and_head_boxes(frame)
            for face in faces:
                detected_faces.append({**face, "sample_time": second})
                if overlay_rect and overlap_fraction(overlay_rect, face) > 0.035:
                    failures.append(f"texto encosta no rosto em {second:.2f}s")
    except Exception as exc:
        failures.append(f"não foi possível concluir a revisão visual: {exc}")
    finally:
        for path in temporary_files:
            path.unlink(missing_ok=True)

    # Confere também as posições encontradas antes da renderização. Isso cobre
    # quadros em que o detector final não reconheça um rosto de perfil.
    for face in metadata.get("face_boxes_mapped_px", []):
        resolution = str(metadata.get("render_resolution", "1080x1920"))
        width, height = (int(value) for value in resolution.split("x", 1))
        normalized_face = {
            "x0": float(face["x0"]) / width,
            "y0": float(face["y0"]) / height,
            "x1": float(face["x1"]) / width,
            "y1": float(face["y1"]) / height,
        }
        if overlay_rect and overlap_fraction(overlay_rect, normalized_face) > 0.035:
            failures.append("texto coincide com rosto detectado na análise de origem")
            break

    unique_failures = list(dict.fromkeys(failures))
    report = {
        "passed": not unique_failures,
        "video": metadata.get("video"),
        "overlay": metadata.get("overlay"),
        "overlay_rect_norm": overlay_rect,
        "faces_checked": len(detected_faces),
        "failures": unique_failures,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if unique_failures:
        raise SystemExit("Reel bloqueado pela revisão visual: " + "; ".join(unique_failures))
    print(
        f"Revisão aprovada: {len(detected_faces)} detecções de rosto verificadas, "
        "texto compacto e enquadramento preservado"
    )


if __name__ == "__main__":
    main()
