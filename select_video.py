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

# Cinco janelas por dia. Em horário de Brasília/Fortaleza:
# 08h, 11h, 14h, 17h e 20h. O UTC correspondente é fixo porque o Brasil
# não usa horário de verão. Workflows podem continuar com oportunidades extras de
# recuperação; fora dessas cinco horas nenhum vídeo é liberado para publicação.
five_daily_platforms = {"instagram", "instagram_underscore", "tiktok"}
target_hours_utc = {11, 14, 17, 20, 23}
if platform in five_daily_platforms and datetime.now(timezone.utc).hour not in target_hours_utc:
    print(json.dumps({
        "count": 0,
        "reason": "outside_five_daily_window",
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

# Os dois Instagrams continuam em conjuntos estruturais exclusivos para não disputar
# o mesmo arquivo. O TikTok usa a pasta completa com histórico próprio permanente:
# isso aumenta o pool disponível sem permitir repetição dentro do TikTok.
platform_bucket = {
    "instagram": 0,
    "instagram_underscore": 1,
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

# REGRA CRÍTICA DO TIKTOK:
# variant_usage é persistido em state_tiktok.json somente após publicação confirmada.
# Portanto qualquer vídeo com uso > 0 já foi efetivamente publicado no TikTok e fica
# inelegível enquanto houver vídeos inéditos na pasta. Não reciclar silenciosamente.
tiktok_used_videos = set()
if platform == "tiktok":
    usage = STATE.get("variant_usage", {})
    if isinstance(usage, dict):
        for name, count in usage.items():
            try:
                if int(count) > 0:
                    tiktok_used_videos.add(str(name))
            except (TypeError, ValueError):
                continue
    blocked.update(tiktok_used_videos)

# Mantém também as exclusões cruzadas já fornecidas pelos workflows. Elas evitam que
# o TikTok pegue imediatamente algo que acabou de sair em um Instagram, sem reduzir
# permanentemente o pool de vídeos inéditos do TikTok.
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
    reason = "no_unused_tiktok_videos" if platform == "tiktok" else "all_videos_blocked"
    print(json.dumps({
        "count": 0,
        "reason": reason,
        "blocked_count": len(blocked),
        "used_tiktok_count": len(tiktok_used_videos),
        "platform": platform,
    }))
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
    "used_tiktok_count": len(tiktok_used_videos),
    "cross_platform_excluded": sorted(blocked),
}, ensure_ascii=False))
