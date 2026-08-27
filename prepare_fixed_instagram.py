from __future__ import annotations

import os
from pathlib import Path

RENDER = Path(__file__).resolve().parent / "render.py"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    if old not in source:
        raise RuntimeError(f"Não encontrei o trecho esperado para {label}; não vou alterar o render às cegas")
    return source.replace(old, new, 1)


def main() -> None:
    source = RENDER.read_text(encoding="utf-8")

    source = replace_once(
        source,
        '    overlay_text = item["overlay"].strip()\n',
        '    overlay_text = os.environ.get("FIXED_OVERLAY_TEXT", item["overlay"]).strip()\n',
        "frase fixa",
    )

    old_style = '''    scale = target_width / 1080\n    radius = max(16, int(22 * scale))\n    shadow_offset = max(3, int(5 * scale))\n    draw.rounded_rectangle(\n        (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n        radius=radius,\n        fill=(0, 0, 0, 52),\n    )\n    draw.rounded_rectangle(\n        (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n        radius=radius,\n        fill=(250, 250, 250, 255),\n        outline=(232, 232, 232, 255),\n        width=max(1, int(2 * scale)),\n    )\n\n    text_height = line_height * len(lines)\n'''

    new_style = '''    scale = target_width / 1080\n    style_index = int(os.environ.get("FIXED_STYLE_INDEX", "0")) % 7\n    radius = max(16, int(22 * scale))\n    shadow_offset = max(3, int(5 * scale))\n    stroke_width = 0\n    stroke_fill = None\n\n    # 7 variações profissionais da MESMA frase. A posição continua sendo decidida\n    # pelo placement seguro para não cobrir rosto/cabeça/sujeito.\n    if style_index == 0:\n        # Cartão branco editorial\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=radius, fill=(0, 0, 0, 50),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=radius, fill=(250, 250, 250, 255),\n            outline=(232, 232, 232, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (18, 18, 18, 255)\n    elif style_index == 1:\n        # Cartão preto minimalista\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=radius, fill=(255, 255, 255, 36),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=radius, fill=(12, 12, 12, 245),\n            outline=(48, 48, 48, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (252, 252, 252, 255)\n    elif style_index == 2:\n        # Sem fundo: branco com contorno preto\n        text_fill = (255, 255, 255, 255)\n        stroke_width = max(2, int(3 * scale))\n        stroke_fill = (0, 0, 0, 240)\n    elif style_index == 3:\n        # Cartão creme premium\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=max(18, int(28 * scale)), fill=(0, 0, 0, 40),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(18, int(28 * scale)), fill=(242, 235, 218, 250),\n            outline=(220, 208, 184, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (35, 31, 25, 255)\n    elif style_index == 4:\n        # Vidro escuro discreto\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(22, int(32 * scale)), fill=(18, 22, 28, 220),\n            outline=(255, 255, 255, 48), width=max(1, int(2 * scale)),\n        )\n        text_fill = (248, 248, 248, 255)\n    elif style_index == 5:\n        # Sem fundo: texto branco com sombra/contorno mais suave\n        text_fill = (255, 255, 255, 255)\n        stroke_width = max(2, int(4 * scale))\n        stroke_fill = (15, 15, 15, 210)\n    else:\n        # Faixa grafite clara, contraste alto sem parecer template genérico\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=max(12, int(16 * scale)), fill=(0, 0, 0, 45),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(12, int(16 * scale)), fill=(225, 227, 230, 248),\n            outline=(198, 201, 205, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (22, 24, 28, 255)\n\n    text_height = line_height * len(lines)\n'''

    source = replace_once(source, old_style, new_style, "sete variações visuais")

    old_draw = '        draw.text((x, y), line, font=font, fill=(18, 18, 18, 255), align="center")\n'
    new_draw = '''        try:\n            from pilmoji import Pilmoji\n            with Pilmoji(image) as pilmoji:\n                pilmoji.text(\n                    (x, y),\n                    line,\n                    font=font,\n                    fill=text_fill,\n                    emoji_scale_factor=0.86,\n                    emoji_position_offset=(0, max(0, int(font.size * 0.06))),\n                    stroke_width=stroke_width,\n                    stroke_fill=stroke_fill,\n                )\n        except Exception:\n            draw.text(\n                (x, y), line, font=font, fill=text_fill, align="center",\n                stroke_width=stroke_width, stroke_fill=stroke_fill,\n            )\n'''
    source = replace_once(source, old_draw, new_draw, "renderização de emojis")

    RENDER.write_text(source, encoding="utf-8")
    print("Perfil fixo aplicado: frase constante, 7 estilos profissionais e emojis habilitados.")


if __name__ == "__main__":
    main()
