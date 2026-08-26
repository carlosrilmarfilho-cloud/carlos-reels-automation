from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata.json"
PAYLOAD = ROOT / "kwai-payload.json"
STATE = ROOT / "state_kwai.json"
KWAI_CAPTION_LIMIT = 300


def adapt_caption(caption: str) -> tuple[str, str]:
    hashtags = re.findall(r"(?<!\w)#[\wÀ-ÿ]+", caption, flags=re.UNICODE)
    body = re.sub(r"(?<!\w)#[\wÀ-ÿ]+", "", caption, flags=re.UNICODE)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    converted: list[str] = []
    for tag in hashtags:
        folded = tag.lower()
        if folded == "#reelsbrasil":
            tag = "#kwaibrasil"
        elif folded == "#reels":
            tag = "#kwai"
        if tag.lower() not in {item.lower() for item in converted}:
            converted.append(tag)

    if not converted:
        converted = ["#kwai", "#kwaibrasil", "#musicabrasileira", "#musica"]
    if not any(tag.lower() == "#kwai" for tag in converted):
        converted.insert(0, "#kwai")

    selected = converted[:5]
    hashtags_text = " ".join(selected)
    separator = "\n\n" if body and hashtags_text else ""
    available = KWAI_CAPTION_LIMIT - len(separator) - len(hashtags_text)
    if len(body) > available:
        body = body[: max(0, available - 1)].rstrip()
        if " " in body:
            body = body.rsplit(" ", 1)[0].rstrip()
        body = f"{body}…" if body else ""

    final_caption = f"{body}{separator}{hashtags_text}".strip()
    return final_caption, hashtags_text


def main() -> None:
    metadata = json.loads(META.read_text(encoding="utf-8"))
    caption, hashtags = adapt_caption(str(metadata.get("caption", "")))
    payload = {
        "platform": "kwai",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "video": metadata.get("video"),
        "theme": metadata.get("theme"),
        "overlay": metadata.get("overlay"),
        "caption": caption,
        "hashtags": hashtags,
        "render_resolution": metadata.get("render_resolution"),
        "quality": {
            "face_overlap_allowed": False,
            "preserve_full_frame": True,
            "explicit_language_allowed": False,
        },
    }
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    state = dict(metadata.get("next_state", {}))
    state["last_posted_at"] = None
    state["last_mode"] = "kwai_mobile_queue"
    state["last_platform"] = "kwai"
    state["last_hashtags"] = hashtags
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Pacote Kwai preparado: {payload['video']} | legenda={len(caption)} chars")


if __name__ == "__main__":
    main()
