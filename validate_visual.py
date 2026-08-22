from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata.json"
OVERLAY = ROOT / "output" / "overlay.png"


def fail(message: str):
    raise SystemExit(f"BLOQUEADO PELA REVISÃO VISUAL: {message}")


def inside(inner, outer, tolerance=0.008):
    return (
        inner["x0"] >= outer["x0"] - tolerance
        and inner["y0"] >= outer["y0"] - tolerance
        and inner["x1"] <= outer["x1"] + tolerance
        and inner["y1"] <= outer["y1"] + tolerance
    )


def main():
    if not META.exists() or not OVERLAY.exists():
        fail("arquivos de renderização ausentes")

    meta = json.loads(META.read_text(encoding="utf-8"))
    overlay = Image.open(OVERLAY).convert("RGBA")
    alpha = overlay.getchannel("A")
    pixel_bbox = alpha.getbbox()
    applied = bool(meta.get("overlay_applied"))

    if not applied:
        if pixel_bbox is not None:
            fail("overlay marcado como desligado, mas ainda há elementos sobre o vídeo")
        print("Revisão visual aprovada: vídeo original preservado; gancho movido para a legenda.")
        return

    safe = meta.get("safe_text_box")
    text_bbox = meta.get("overlay_text_bbox_norm")
    if not isinstance(safe, dict) or not isinstance(text_bbox, dict):
        fail("texto no vídeo sem área livre revisada")
    if not inside(text_bbox, safe):
        fail("texto saiu da área livre revisada")
    if pixel_bbox is None:
        fail("overlay marcado como ativo, mas está vazio")

    width, height = overlay.size
    x0, y0, x1, y1 = pixel_bbox
    bbox_width = (x1 - x0) / width
    bbox_height = (y1 - y0) / height
    opaque_pixels = sum(alpha.histogram()[1:])
    coverage = opaque_pixels / (width * height)

    if bbox_width > 0.90:
        fail("texto largo demais")
    if bbox_height > 0.18:
        fail("texto alto demais")
    if coverage > 0.055:
        fail("overlay ocupa área excessiva do quadro")

    print(
        "Revisão visual aprovada: texto compacto, sem caixa preta e contido "
        "na área livre revisada."
    )


if __name__ == "__main__":
    main()
