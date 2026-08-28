from __future__ import annotations

from pathlib import Path

RENDER = Path(__file__).resolve().parent / "render.py"
FIXED_TEXT = "Tá aí a terapia que você precisa"


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
        f'    overlay_text = {FIXED_TEXT!r}\n',
        "frase fixa sem emojis",
    )

    old_style = '''    scale = target_width / 1080\n    radius = max(16, int(22 * scale))\n    shadow_offset = max(3, int(5 * scale))\n    draw.rounded_rectangle(\n        (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n        radius=radius,\n        fill=(0, 0, 0, 52),\n    )\n    draw.rounded_rectangle(\n        (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n        radius=radius,\n        fill=(250, 250, 250, 255),\n        outline=(232, 232, 232, 255),\n        width=max(1, int(2 * scale)),\n    )\n\n    text_height = line_height * len(lines)\n'''

    new_style = '''    scale = target_width / 1080\n    style_index = int(load_json(STATE, {}).get("posts_total", 0)) % 7\n    radius = max(16, int(22 * scale))\n    shadow_offset = max(3, int(5 * scale))\n    stroke_width = 0\n    stroke_fill = None\n\n    # 7 variações profissionais da MESMA frase. A posição continua sendo decidida\n    # pelo placement seguro para não cobrir rosto/cabeça/sujeito.\n    if style_index == 0:\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=radius, fill=(0, 0, 0, 50),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=radius, fill=(250, 250, 250, 255),\n            outline=(232, 232, 232, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (18, 18, 18, 255)\n    elif style_index == 1:\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=radius, fill=(255, 255, 255, 36),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=radius, fill=(12, 12, 12, 245),\n            outline=(48, 48, 48, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (252, 252, 252, 255)\n    elif style_index == 2:\n        text_fill = (255, 255, 255, 255)\n        stroke_width = max(2, int(3 * scale))\n        stroke_fill = (0, 0, 0, 240)\n    elif style_index == 3:\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=max(18, int(28 * scale)), fill=(0, 0, 0, 40),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(18, int(28 * scale)), fill=(242, 235, 218, 250),\n            outline=(220, 208, 184, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (35, 31, 25, 255)\n    elif style_index == 4:\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(22, int(32 * scale)), fill=(18, 22, 28, 220),\n            outline=(255, 255, 255, 48), width=max(1, int(2 * scale)),\n        )\n        text_fill = (248, 248, 248, 255)\n    elif style_index == 5:\n        text_fill = (255, 255, 255, 255)\n        stroke_width = max(2, int(4 * scale))\n        stroke_fill = (15, 15, 15, 210)\n    else:\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"] + shadow_offset, rect["x1"], rect["y1"] + shadow_offset),\n            radius=max(12, int(16 * scale)), fill=(0, 0, 0, 45),\n        )\n        draw.rounded_rectangle(\n            (rect["x0"], rect["y0"], rect["x1"], rect["y1"]),\n            radius=max(12, int(16 * scale)), fill=(225, 227, 230, 248),\n            outline=(198, 201, 205, 255), width=max(1, int(2 * scale)),\n        )\n        text_fill = (22, 24, 28, 255)\n\n    text_height = line_height * len(lines)\n'''

    source = replace_once(source, old_style, new_style, "sete variações visuais")

    old_draw = '        draw.text((x, y), line, font=font, fill=(18, 18, 18, 255), align="center")\n'
    new_draw = '''        draw.text(\n            (x, y), line, font=font, fill=text_fill, align="center",\n            stroke_width=stroke_width, stroke_fill=stroke_fill,\n        )\n'''
    source = replace_once(source, old_draw, new_draw, "renderização sem emojis")

    RENDER.write_text(source, encoding="utf-8")
    print(f"Perfil fixo aplicado: '{FIXED_TEXT}', 7 estilos profissionais e nenhum emoji.")


if __name__ == "__main__":
    main()
