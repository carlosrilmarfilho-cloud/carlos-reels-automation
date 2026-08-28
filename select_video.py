from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = json.loads((ROOT / "video_profiles.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
valid_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
platform = os.environ.get("PLATFORM", "").strip().lower()

# Sete janelas por dia, espalhadas a cada duas horas. Em horário de Brasília/Fortaleza:
# 08h, 10h, 12h, 14h, 16h, 18h e 20h. O UTC correspondente é fixo porque o Brasil
# não usa horário de verão. Workflows podem continuar com oportunidades extras de
# recuperação; fora dessas sete horas nenhum vídeo é liberado para publicação.
seven_daily_platforms = {"instagram", "instagram_underscore", "tiktok"}
target_hours_utc = {11, 13, 15, 17, 19, 21, 23}
if platform in seven_daily_platforms and datetime.now(timezone.utc).hour not in target_hours_utc:
    print(json.dumps({
        "count": 0,
        "reason": "outside_seven_daily_window",
        "platform": platform,
        "target_hours_utc": sorted(target_hours_utc),
    }))
    raise SystemExit(0)

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

# Divide estruturalmente a pasta em três conjuntos exclusivos. Assim o mesmo arquivo
# nunca é escolhido pelo TikTok e pelos dois Instagrams. A divisão é estável pelo nome
# do arquivo: adicionar vídeos novos não embaralha os já existentes entre plataformas.
platform_bucket = {
    "instagram": 0,
    "instagram_underscore": 1,
    "tiktok": 2,
}.get(platform)
if platform_bucket is not None:
    def bucket_for(name: str) -> int:
        digest = hashlib.sha256(name.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % 3

    ordered_names = [name for name in ordered_names if bucket_for(name) == platform_bucket]

if not ordered_names:
    print(json.dumps({"count": 0, "reason": "no_videos_for_platform", "platform": platform}))
    raise SystemExit(0)

idx = int(STATE.get("video_index", 0)) % len(ordered_names)
blocked = set(STATE.get("blocked_videos", []))

# Nunca repete imediatamente o último vídeo da própria plataforma.
last_video = str(STATE.get("last_video", "")).strip()
if last_video:
    blocked.add(last_video)

# Mantém também as exclusões cruzadas já fornecidas pelos workflows. Elas são uma
# proteção adicional; a separação por conjuntos acima é a garantia principal.
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
    print(json.dumps({"count": 0, "blocked_count": len(blocked), "platform": platform}))
    raise SystemExit(0)

selected = by_name[name]
print(json.dumps({
    "count": len(ordered_names),
    "index": idx,
    "name": name,
    "url": selected["url"],
    "path": selected["path"],
    "platform": platform,
    "platform_bucket": platform_bucket,
    "cross_platform_excluded": sorted(blocked),
}, ensure_ascii=False))
