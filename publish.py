from __future__ import annotations
import json, os, time, traceback
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata.json"
STATE = ROOT / "state.json"
DIAG = ROOT / "diagnostic.json"
TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
VIDEO_URL = os.environ.get("PUBLIC_VIDEO_URL", "").strip()
API_VERSION = os.environ.get("IG_API_VERSION", "v26.0").strip()
TRIAL_REEL = os.environ.get("TRIAL_REEL", "true").strip().lower() in {"1", "true", "yes", "sim"}

if not TOKEN:
    raise SystemExit("INSTAGRAM_ACCESS_TOKEN não configurado")
if not VIDEO_URL:
    raise SystemExit("PUBLIC_VIDEO_URL não configurado")

BASE = f"https://graph.instagram.com/{API_VERSION}"
diag = {"started_at": datetime.now(timezone.utc).isoformat(), "mode": "trial" if TRIAL_REEL else "normal", "stage": "start"}


def save_diag(**extra):
    diag.update(extra)
    DIAG.write_text(json.dumps(diag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api(method, path, **kwargs):
    url = path if path.startswith("http") else BASE + path
    kwargs.setdefault("timeout", 120)
    r = requests.request(method, url, **kwargs)
    if not r.ok:
        try:
            body = r.json()
        except Exception:
            body = r.text[:1200]
        raise RuntimeError(f"Instagram API {r.status_code}: {json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else body}")
    return r.json()


def wait_public(url):
    for _ in range(24):
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.ok and int(r.headers.get("content-length", "1")) > 0:
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError("O vídeo ainda não ficou público no GitHub Raw")


def main():
    try:
        meta = json.loads(META.read_text(encoding="utf-8"))
        caption = meta["caption"]
        save_diag(stage="auth")
        me = api("GET", "/me", params={"fields": "id,username", "access_token": TOKEN})
        ig_id = me["id"]
        save_diag(stage="video_public", username=me.get("username"), ig_id=ig_id)

        wait_public(VIDEO_URL)
        payload = {
            "media_type": "REELS",
            "video_url": VIDEO_URL,
            "caption": caption,
            "share_to_feed": "false" if TRIAL_REEL else "true",
            "access_token": TOKEN,
        }
        if TRIAL_REEL:
            payload["trial_params"] = json.dumps({"graduation_strategy": "MANUAL"})
        save_diag(stage="create_container")
        container = api("POST", f"/{ig_id}/media", data=payload)
        cid = container["id"]
        save_diag(stage="container_processing", container_id=cid)

        status = None
        last_status = None
        for _ in range(40):
            data = api("GET", f"/{cid}", params={"fields": "status_code,status", "access_token": TOKEN})
            status = data.get("status_code")
            last_status = data.get("status")
            if status == "FINISHED":
                break
            if status in {"ERROR", "EXPIRED"}:
                raise RuntimeError(f"Falha no processamento: {data}")
            time.sleep(5)
        if status != "FINISHED":
            raise RuntimeError(f"Timeout aguardando processamento do Reel. Último status: {status} / {last_status}")

        save_diag(stage="publish", container_status=status)
        published = api("POST", f"/{ig_id}/media_publish", data={"creation_id": cid, "access_token": TOKEN})
        media_id = published.get("id")

        state = meta["next_state"]
        state["last_posted_at"] = datetime.now(timezone.utc).isoformat()
        state["last_mode"] = "trial" if TRIAL_REEL else "normal"
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_diag(stage="success", success=True, media_id=media_id, finished_at=datetime.now(timezone.utc).isoformat())
        print(f"Reel publicado: {media_id}")
    except Exception as e:
        save_diag(stage=diag.get("stage", "unknown"), success=False, error_type=type(e).__name__, error=str(e)[:1800], finished_at=datetime.now(timezone.utc).isoformat())
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
