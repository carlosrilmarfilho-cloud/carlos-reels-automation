from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COPY_PATH = ROOT / "viral_copy.json"
PROFILES_PATH = ROOT / "video_profiles.json"


def normalize(value: str) -> str:
    return " ".join(str(value).split()).strip()


def main() -> None:
    bank = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8")) if PROFILES_PATH.exists() else {}
    legacy = profiles.get("themes", {})

    for theme, old_items in legacy.items():
        section = bank.get(theme)
        if not isinstance(section, dict):
            continue
        old_overlays = {normalize(item.get("overlay", "")) for item in old_items}
        old_captions = {normalize(item.get("caption", "")) for item in old_items}

        overlays = [
            normalize(value)
            for value in section.get("overlays", [])
            if normalize(value) and normalize(value) not in old_overlays
        ]
        captions = [
            normalize(value)
            for value in section.get("captions", [])
            if normalize(value) and normalize(value) not in old_captions
        ]

        # render.py exige estes limites. Falhamos cedo se uma linha editorial escapar deles.
        overlays = [value for value in overlays if 16 <= len(value) <= 82]
        captions = [value for value in captions if 20 <= len(value) <= 220]

        if overlays:
            section["overlays"] = overlays
        if captions:
            section["captions"] = captions

    COPY_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Banco legado removido do sorteio; limites editoriais validados.")


if __name__ == "__main__":
    main()
