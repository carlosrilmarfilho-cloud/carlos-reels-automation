from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = json.loads((ROOT / "video_profiles.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))
LEDGER_PATH = ROOT / "tiktok-used-ledger.json"

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
valid_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
platform = os.environ.get("PLATFORM", "").strip().lower()

target_hours_utc = {11, 14, 17, 20, 23}
if platform in {"instagram", "instagram_underscore", "tiktok"} and datetime.now(timezone.utc).hour not in target_hours_utc:
    print(json.dumps({"count": 0, "reason": "outside_five_daily_window", "platform": platform}))
    raise SystemExit(0)


def drive_id_from_url(url: str) -> str:
    for pattern in (r"/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)", r"/uc\?id=([A-Za-z0-9_-]+)"):
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


# gdown may repeat rows. Keep one row per stable Drive ID/URL, then one choice per
# filename. Duplicate filenames in Drive remain ineligible together once that source
# name is in the reconstructed legacy ledger.
by_identity = {}
for item in raw:
    path = str(item.get("path", ""))
    url = str(item.get("url", ""))
    if not url or Path(path).suffix.lower() not in valid_ext:
        continue
    drive_id = str(item.get("id") or drive_id_from_url(url)).strip()
    identity = drive_id or url
    by_identity[identity] = {"url": url, "path": path, "name": Path(path).name, "drive_id": drive_id}

by_name = {}
for item in by_identity.values():
    by_name.setdefault(item["name"], item)

queue_file_raw = os.environ.get("VIDEO_QUEUE_FILE", "").strip()
if platform in {"instagram", "instagram_underscore", "tiktok"}:
    if not queue_file_raw:
        print(json.dumps({"count": 0, "reason": "platform_fifo_queue_not_configured", "platform": platform}))
        raise SystemExit(0)
    queue_path = ROOT / queue_file_raw
    if not queue_path.exists():
        print(json.dumps({"count": 0, "reason": "platform_fifo_queue_missing", "platform": platform}))
        raise SystemExit(0)
    queue_state = json.loads(queue_path.read_text(encoding="utf-8"))
    if str(queue_state.get("platform") or "") != platform:
        raise SystemExit(f"Fila {queue_path.name} pertence a outra plataforma")

    current_by_id = {
        item["drive_id"]: item for item in by_identity.values() if item.get("drive_id")
    }
    synchronized = []
    seen_ids = set()
    # Remoções preservam a ordem relativa dos itens restantes.
    for old in queue_state.get("queue", []):
        drive_id = str(old.get("drive_id") or "").strip()
        if drive_id and drive_id in current_by_id and drive_id not in seen_ids:
            synchronized.append({**old, **current_by_id[drive_id]})
            seen_ids.add(drive_id)
    # Novos arquivos entram somente no fim da fila.
    for drive_id, item in current_by_id.items():
        if drive_id not in seen_ids:
            synchronized.append(item)
            seen_ids.add(drive_id)

    queue_state["queue"] = synchronized
    queue_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    queue_state["source_count"] = len(synchronized)
    queue_path.write_text(json.dumps(queue_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not synchronized:
        print(json.dumps({"count": 0, "reason": "fifo_source_pool_empty", "platform": platform}))
        raise SystemExit(0)

    selected = synchronized[0]
    print(json.dumps({
        "count": len(synchronized),
        "index": 0,
        "name": selected["name"],
        "url": selected["url"],
        "path": selected["path"],
        "drive_id": selected["drive_id"],
        "platform": platform,
        "queue_file": queue_path.name,
        "fifo_front": True,
    }, ensure_ascii=False))
    raise SystemExit(0)

preferred = [n for n in PROFILES.get("rotation", []) if n in by_name]
ordered_names = preferred + sorted(n for n in by_name if n not in preferred)

platform_bucket = {"instagram": 0, "instagram_underscore": 1}.get(platform)
if platform_bucket is not None:
    def bucket_for(name: str) -> int:
        digest = hashlib.sha256(name.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % 3
    ordered_names = [name for name in ordered_names if bucket_for(name) == platform_bucket]

if not ordered_names:
    print(json.dumps({"count": 0, "reason": "no_videos_for_platform", "platform": platform}))
    raise SystemExit(0)

idx = int(STATE.get("video_index", 0)) % len(ordered_names)
blocked_names = set(STATE.get("blocked_videos", []))
blocked_ids = set()
last_video = str(STATE.get("last_video", "")).strip()
if last_video:
    blocked_names.add(last_video)

if platform == "tiktok":
    if not LEDGER_PATH.exists():
        print(json.dumps({"count": 0, "reason": "tiktok_ledger_missing", "platform": platform}))
        raise SystemExit(0)
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    blocked_names.update(str(x) for x in ledger.get("used_video_names", []) if str(x))
    blocked_ids.update(str(x) for x in ledger.get("used_drive_ids", []) if str(x))
    # Backward-compatible conservative protection while old state is retired.
    for name, count in (STATE.get("variant_usage", {}) or {}).items():
        try:
            if int(count) > 0:
                blocked_names.add(str(name))
        except (TypeError, ValueError):
            pass

for value in os.environ.get("CROSS_PLATFORM_EXCLUDES", "").split("|"):
    value = value.strip()
    if value:
        blocked_names.add(value)

for step in range(len(ordered_names)):
    candidate_idx = (idx + step) % len(ordered_names)
    candidate = by_name[ordered_names[candidate_idx]]
    if candidate["name"] in blocked_names or (candidate["drive_id"] and candidate["drive_id"] in blocked_ids):
        continue
    idx = candidate_idx
    selected = candidate
    break
else:
    print(json.dumps({
        "count": 0,
        "reason": "tiktok_pool_exhausted" if platform == "tiktok" else "all_videos_blocked",
        "platform": platform,
        "used_tiktok_names": len(blocked_names) if platform == "tiktok" else 0,
        "used_tiktok_drive_ids": len(blocked_ids),
    }))
    raise SystemExit(0)

print(json.dumps({
    "count": len(ordered_names),
    "index": idx,
    "name": selected["name"],
    "url": selected["url"],
    "path": selected["path"],
    "drive_id": selected["drive_id"],
    "platform": platform,
    "platform_bucket": platform_bucket,
}, ensure_ascii=False))
