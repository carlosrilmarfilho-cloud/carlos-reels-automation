from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = json.loads((ROOT / "video_profiles.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
valid_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

# gdown --json may return repeated entries; dedupe by URL first.
by_url = {}
for item in raw:
    path = str(item.get("path", ""))
    url = str(item.get("url", ""))
    if not url or Path(path).suffix.lower() not in valid_ext:
        continue
    by_url[url] = {"url": url, "path": path, "name": Path(path).name}

items = list(by_url.values())
by_name = {x["name"]: x for x in items}
preferred = [n for n in PROFILES.get("rotation", []) if n in by_name]
unknown = sorted([n for n in by_name if n not in preferred])
ordered_names = preferred + unknown

if not ordered_names:
    print(json.dumps({"count": 0}))
    raise SystemExit(0)

idx = int(STATE.get("video_index", 0)) % len(ordered_names)
blocked = set(STATE.get("blocked_videos", []))

# Nunca repete imediatamente o último vídeo da própria plataforma.
last_video = str(STATE.get("last_video", "")).strip()
if last_video:
    blocked.add(last_video)

# Os workflows são escalonados dentro de cada hora. Cada um passa aqui os
# últimos vídeos confirmados nas outras plataformas, garantindo que Instagram,
# TikTok e Kwai não publiquem o mesmo arquivo no mesmo ciclo horário.
for value in os.environ.get("CROSS_PLATFORM_EXCLUDES", "").split("|"):
    value = value.strip()
    if value:
        blocked.add(value)

for step in range(len(ordered_names)):
    candidate_idx = (idx + step) % len(ordered_names)
    candidate_name = ordered_names[candidate_idx]
    if candidate_name not in blocked:
        idx = candidate_idx
        name = candidate_name
        break
else:
    print(json.dumps({"count": 0, "blocked_count": len(blocked)}))
    raise SystemExit(0)

selected = by_name[name]
print(json.dumps({
    "count": len(ordered_names),
    "index": idx,
    "name": name,
    "url": selected["url"],
    "path": selected["path"],
    "cross_platform_excluded": sorted(blocked),
}, ensure_ascii=False))
