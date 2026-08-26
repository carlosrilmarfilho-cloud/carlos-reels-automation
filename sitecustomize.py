from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# GitHub Actions define GITHUB_ACTIONS=true. Fora da automação, este arquivo não altera nada.
if os.getenv("GITHUB_ACTIONS") == "true":
    root = Path(__file__).resolve().parent
    render_path = root / "render.py"

    if render_path.exists():
        source = render_path.read_text(encoding="utf-8")
        replacements = {
            "used_overlays = set(recent_overlay_values)": "used_overlays = set(recent_overlay_values[-28:])",
            "overlay_signature(value) for value in recent_overlay_values[-60:]": "overlay_signature(value) for value in recent_overlay_values[-28:]",
            "overlay_opening_signature(value) for value in recent_overlay_values[-60:]": "overlay_opening_signature(value) for value in recent_overlay_values[-28:]",
            "used_captions = set(recent_caption_values)": "used_captions = set(recent_caption_values[-28:])",
            "caption_signature(value) for value in recent_caption_values[-60:]": "caption_signature(value) for value in recent_caption_values[-28:]",
            "caption_opening_signature(value) for value in recent_caption_values[-60:]": "caption_opening_signature(value) for value in recent_caption_values[-28:]",
            "caption_opening_ngrams(value) for value in recent_caption_values[-60:]": "caption_opening_ngrams(value) for value in recent_caption_values[-28:]",
        }
        for old, new in replacements.items():
            source = source.replace(old, new)
        render_path.write_text(source, encoding="utf-8")

    # O banco específico continua mandando na frase do vídeo. Na legenda, somamos o banco
    # musical genérico para ampliar variedade sem trocar o assunto do overlay.
    if Path(sys.argv[0]).name == "render.py":
        copy_path = root / "viral_copy.json"
        if copy_path.exists():
            bank = json.loads(copy_path.read_text(encoding="utf-8"))
            generic_captions = list(bank.get("generic", {}).get("captions", []))
            for theme in (
                "forro_antigo",
                "brega",
                "romantica",
                "saudade",
                "musica_terapia",
                "nordeste_identidade",
                "brasileiro_exterior",
            ):
                section = bank.get(theme)
                if not isinstance(section, dict):
                    continue
                captions = list(section.get("captions", []))
                for caption in generic_captions:
                    if caption not in captions:
                        captions.append(caption)
                section["captions"] = captions
            copy_path.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
