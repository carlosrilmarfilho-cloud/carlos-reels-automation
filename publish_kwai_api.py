from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "output" / "reel.mp4"
PAYLOAD = ROOT / "kwai-payload.json"
LIVE_STATE = ROOT / "state_kwai.json"
PENDING_STATE = ROOT / "state_kwai_pending.json"
TOKEN_STORE = ROOT / "kwai-token-state.enc"
RESULT_FILE = ROOT / "kwai-publish-result.json"

OPEN_BASE = "https://open.kuaishou.com"
CHUNK_SIZE = 8 * 1024 * 1024
REFRESH_MARGIN_SECONDS = 6 * 60 * 60
TIMEOUT = 120


class KwaiApiError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise KwaiApiError(f"Secret ausente: {name}")
    return value


def fernet_for(secret: str) -> Fernet:
    digest = hashlib.sha256(("carlos-kwai-token-store-v1:" + secret).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def read_json_response(response: requests.Response, action: str) -> dict:
    try:
        data = response.json()
    except Exception as exc:
        raise KwaiApiError(f"{action}: resposta não-JSON HTTP {response.status_code}") from exc
    if not response.ok:
        raise KwaiApiError(f"{action}: HTTP {response.status_code}: {data}")
    if data.get("result") != 1:
        raise KwaiApiError(f"{action}: API recusou a operação: {data}")
    return data


def save_token_state(bundle: dict, app_secret: str) -> None:
    safe = {
        "access_token": bundle["access_token"],
        "refresh_token": bundle["refresh_token"],
        "access_expires_at": int(bundle["access_expires_at"]),
        "refresh_expires_at": int(bundle.get("refresh_expires_at", 0)),
        "scopes": bundle.get("scopes", []),
        "open_id": bundle.get("open_id", ""),
        "updated_at": now_iso(),
    }
    encrypted = fernet_for(app_secret).encrypt(json.dumps(safe).encode("utf-8"))
    TOKEN_STORE.write_bytes(encrypted + b"\n")


def load_token_state(app_secret: str) -> dict | None:
    if not TOKEN_STORE.exists():
        return None
    try:
        raw = TOKEN_STORE.read_bytes().strip()
        decoded = fernet_for(app_secret).decrypt(raw)
        return json.loads(decoded.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise KwaiApiError("Não foi possível abrir o cofre de token do Kwai.") from exc


def require_publish_scope(bundle: dict) -> None:
    scopes = bundle.get("scopes") or []
    if "user_video_publish" not in scopes:
        raise KwaiApiError(
            "O token foi emitido sem a permissão user_video_publish. A conta/app precisa autorizar publicação de vídeo."
        )


def refresh_tokens(app_id: str, app_secret: str, refresh_token: str) -> dict:
    response = requests.get(
        f"{OPEN_BASE}/oauth2/refresh_token",
        params={
            "app_id": app_id,
            "app_secret": app_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    data = read_json_response(response, "refresh token")
    scopes = data.get("scopes") or []
    now = int(time.time())
    bundle = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "access_expires_at": now + int(data.get("expires_in", 172800)),
        "refresh_expires_at": now + int(data.get("refresh_token_expires_in", 0)),
        "scopes": scopes,
        "open_id": data.get("open_id", ""),
    }
    require_publish_scope(bundle)
    return bundle


def get_access_bundle(app_id: str, app_secret: str) -> dict:
    bundle = load_token_state(app_secret)
    if bundle is None:
        initial_refresh = require_env("KWAI_INITIAL_REFRESH_TOKEN")
        bundle = refresh_tokens(app_id, app_secret, initial_refresh)
        save_token_state(bundle, app_secret)
        return bundle

    require_publish_scope(bundle)
    if int(bundle.get("access_expires_at", 0)) <= int(time.time()) + REFRESH_MARGIN_SECONDS:
        bundle = refresh_tokens(app_id, app_secret, bundle["refresh_token"])
        save_token_state(bundle, app_secret)
    return bundle


def start_upload(app_id: str, access_token: str) -> tuple[str, str]:
    response = requests.post(
        f"{OPEN_BASE}/openapi/photo/start_upload",
        params={"access_token": access_token, "app_id": app_id},
        timeout=TIMEOUT,
    )
    data = read_json_response(response, "iniciar upload")
    return str(data["upload_token"]), str(data["endpoint"])


def upload_video(video_path: Path, upload_token: str, endpoint: str) -> None:
    base = endpoint if endpoint.startswith(("http://", "https://")) else f"http://{endpoint}"
    size = video_path.stat().st_size

    if size < 10 * 1024 * 1024:
        with video_path.open("rb") as handle:
            response = requests.post(
                f"{base}/api/upload",
                params={"upload_token": upload_token},
                data=handle,
                headers={"Content-Type": "video/mp4"},
                timeout=TIMEOUT,
            )
        read_json_response(response, "upload direto")
        return

    fragment_count = math.ceil(size / CHUNK_SIZE)
    with video_path.open("rb") as handle:
        for fragment_id in range(fragment_count):
            chunk = handle.read(CHUNK_SIZE)
            response = requests.post(
                f"{base}/api/upload/fragment",
                params={"upload_token": upload_token, "fragment_id": fragment_id},
                data=chunk,
                headers={"Content-Type": "video/mp4"},
                timeout=TIMEOUT,
            )
            read_json_response(response, f"upload fragmento {fragment_id + 1}/{fragment_count}")

    response = requests.post(
        f"{base}/api/upload/complete",
        params={"upload_token": upload_token, "fragment_count": fragment_count},
        timeout=TIMEOUT,
    )
    read_json_response(response, "finalizar upload fragmentado")


def make_cover(video_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="kwai-cover-")) / "cover.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "0.5",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(tmp),
    ]
    subprocess.run(cmd, check=True)
    if not tmp.exists() or tmp.stat().st_size == 0:
        raise KwaiApiError("Não consegui gerar a capa JPG do vídeo.")
    return tmp


def publish_video(app_id: str, access_token: str, upload_token: str, caption: str, cover: Path) -> dict:
    with cover.open("rb") as cover_handle:
        response = requests.post(
            f"{OPEN_BASE}/openapi/photo/publish",
            params={
                "access_token": access_token,
                "app_id": app_id,
                "upload_token": upload_token,
            },
            data={"caption": caption, "stereo_type": "NOT_SPHERICAL_VIDEO"},
            files={"cover": ("cover.jpg", cover_handle, "image/jpeg")},
            timeout=TIMEOUT,
        )
    return read_json_response(response, "publicar vídeo")


def commit_success_state(video_info: dict) -> None:
    pending_already_advanced = PENDING_STATE.exists()
    if pending_already_advanced:
        state = json.loads(PENDING_STATE.read_text(encoding="utf-8"))
    elif LIVE_STATE.exists():
        state = json.loads(LIVE_STATE.read_text(encoding="utf-8"))
    else:
        state = {}

    # metadata.next_state já incrementa posts_total e video_index. Quando existe
    # estado pendente, apenas confirmamos a publicação; não incrementamos de novo.
    if not pending_already_advanced:
        state["posts_total"] = int(state.get("posts_total", 0)) + 1
    state["last_posted_at"] = now_iso()
    state["last_mode"] = "kwai_server_api"
    state["last_platform"] = "kwai"
    state["last_publish_id"] = video_info.get("photo_id") or video_info.get("photoId") or ""
    LIVE_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PENDING_STATE.unlink(missing_ok=True)


def main() -> None:
    app_id = require_env("KWAI_APP_ID")
    app_secret = require_env("KWAI_APP_SECRET")
    if not VIDEO.exists():
        raise KwaiApiError(f"Vídeo não encontrado: {VIDEO}")
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    caption = str(payload.get("caption", "")).strip()
    if not caption:
        raise KwaiApiError("Legenda Kwai vazia.")

    bundle = get_access_bundle(app_id, app_secret)
    upload_token, endpoint = start_upload(app_id, bundle["access_token"])
    upload_video(VIDEO, upload_token, endpoint)
    cover = make_cover(VIDEO)
    result = publish_video(app_id, bundle["access_token"], upload_token, caption, cover)
    video_info = result.get("video_info") or result.get("videoInfo") or {}

    safe_result = {
        "published_at": now_iso(),
        "result": result.get("result"),
        "photo_id": video_info.get("photo_id") or video_info.get("photoId"),
        "caption": video_info.get("caption", caption),
        "cover": video_info.get("cover"),
        "play_url": video_info.get("play_url") or video_info.get("playUrl"),
        "pending": video_info.get("pending"),
    }
    RESULT_FILE.write_text(json.dumps(safe_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    commit_success_state(video_info)
    print(f"Kwai publicado via servidor: {safe_result['photo_id'] or 'ID pendente'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        RESULT_FILE.write_text(
            json.dumps({"published_at": None, "error": str(exc), "failed_at": now_iso()}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        raise
