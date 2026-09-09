from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

queue_path = Path(sys.argv[1])
candidate_path = Path(sys.argv[2])
queue_state = json.loads(queue_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
queue = list(queue_state.get("queue") or [])
if not queue:
    raise SystemExit("Fila FIFO vazia; confirmação bloqueada")
front = queue[0]
if str(front.get("drive_id") or "") != str(candidate.get("drive_id") or ""):
    raise SystemExit(
        f"Frente FIFO mudou: esperado {front.get('drive_id')}, candidato {candidate.get('drive_id')}"
    )
confirmed = dict(queue.pop(0))
if candidate.get("sha256"):
    confirmed["sha256"] = str(candidate["sha256"]).lower()
queue.append(confirmed)
now = datetime.now(timezone.utc).isoformat()
history = list(queue_state.get("history") or [])
history.append({
    "confirmed_at": now,
    "drive_id": confirmed.get("drive_id"),
    "name": confirmed.get("name"),
    "sha256": confirmed.get("sha256"),
})
queue_state.update({
    "queue": queue,
    "completed_rotations": int(queue_state.get("completed_rotations") or 0) + 1,
    "last_confirmed": history[-1],
    "updated_at": now,
    "history": history[-200:],
})
queue_path.write_text(json.dumps(queue_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"rotated": True, "next_drive_id": queue[0].get("drive_id")}, ensure_ascii=False))
