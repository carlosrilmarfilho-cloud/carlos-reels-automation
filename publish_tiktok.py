from __future__ import annotations

import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata.json"
STATE = ROOT / "state_tiktok.json"
DIAG = ROOT / "tiktok-diagnostic.json"
VIDEO_URL = os.environ.get("PUBLIC_VIDEO_URL", "").strip()
CHANNEL_OVERRIDE = os.environ.get("BUFFER_TIKTOK_CHANNEL_ID", "").strip()
BUFFER_API = "https://api.buffer.com"
TIKTOK_DESCRIPTION_LIMIT = 150


def normalize_api_key(raw: str) -> str:
    value = raw.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    if not value:
        raise SystemExit("BUFFER_API_KEY não configurado")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise SystemExit(
            "BUFFER_API_KEY contém caracteres inválidos. Salve no GitHub somente a chave pura do Buffer, "
            "sem 'Bearer', aspas, rótulos, espaços ou emojis."
        ) from exc
    if any(character.isspace() for character in value):
        raise SystemExit(
            "BUFFER_API_KEY contém espaços/quebras de linha. Salve somente a chave pura do Buffer."
        )
    return value


BUFFER_API_KEY = normalize_api_key(os.environ.get("BUFFER_API_KEY", ""))

if not VIDEO_URL:
    raise SystemExit("PUBLIC_VIDEO_URL não configurado")


diag = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "platform": "tiktok",
    "publisher": "buffer",
    "stage": "start",
}


def save_diag(**extra):
    diag.update(extra)
    DIAG.write_text(json.dumps(diag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def graphql(query: str) -> dict:
    response = requests.post(
        BUFFER_API,
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"Buffer API HTTP {response.status_code}: {response.text[:1200]}")
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"Buffer GraphQL: {json.dumps(payload['errors'], ensure_ascii=False)[:1800]}")
    return payload.get("data", {})


def gql_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def wait_public(url: str) -> None:
    for _ in range(24):
        try:
            response = requests.get(url, timeout=30, stream=True)
            if response.ok:
                length = int(response.headers.get("content-length", "1") or "1")
                if length > 0:
                    return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError("O vídeo ainda não ficou público para o Buffer")


def find_tiktok_channel() -> tuple[str, str]:
    if CHANNEL_OVERRIDE:
        return CHANNEL_OVERRIDE, "override"

    account = graphql(
        """
        query GetOrganizations {
          account {
            organizations {
              id
              name
            }
          }
        }
        """
    )
    organizations = account.get("account", {}).get("organizations", [])
    channels: list[dict] = []
    for organization in organizations:
        organization_id = str(organization.get("id", ""))
        if not organization_id:
            continue
        data = graphql(
            f"""
            query GetChannels {{
              channels(input: {{ organizationId: {gql_string(organization_id)} }}) {{
                id
                name
                displayName
                service
              }}
            }}
            """
        )
        channels.extend(data.get("channels", []))

    tiktok_channels = [
        channel for channel in channels
        if str(channel.get("service", "")).lower() == "tiktok"
    ]
    if not tiktok_channels:
        raise RuntimeError("Nenhum canal TikTok conectado ao Buffer")
    if len(tiktok_channels) > 1:
        options = ", ".join(
            f"{channel.get('displayName') or channel.get('name')} ({channel.get('id')})"
            for channel in tiktok_channels
        )
        raise RuntimeError(
            "Há mais de um TikTok no Buffer. Configure BUFFER_TIKTOK_CHANNEL_ID. "
            f"Canais encontrados: {options}"
        )
    channel = tiktok_channels[0]
    return str(channel["id"]), str(channel.get("displayName") or channel.get("name") or "TikTok")


def truncate_body(body: str, max_chars: int) -> str:
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) <= max_chars:
        return body
    if max_chars <= 1:
        return ""
    clipped = body[: max_chars - 1].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip()
    return (clipped + "…").strip()


def adapt_caption_for_tiktok(caption: str) -> tuple[str, str]:
    hashtags = re.findall(r"(?<!\w)#[\wÀ-ÿ]+", caption, flags=re.UNICODE)
    body = re.sub(r"(?<!\w)#[\wÀ-ÿ]+", "", caption, flags=re.UNICODE)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    converted: list[str] = []
    for tag in hashtags:
        folded = tag.lower()
        if folded == "#reelsbrasil":
            tag = "#tiktokbrasil"
        elif folded == "#reels":
            tag = "#paravoce"
        if tag.lower() not in {item.lower() for item in converted}:
            converted.append(tag)

    if not converted:
        converted = ["#tiktokbrasil", "#musicabrasileira", "#musica"]

    selected: list[str] = []
    for tag in converted[:5]:
        candidate = " ".join(selected + [tag])
        if len(candidate) <= 72:
            selected.append(tag)
    hashtags_text = " ".join(selected)

    separator = "\n\n" if body and hashtags_text else ""
    available_for_body = TIKTOK_DESCRIPTION_LIMIT - len(separator) - len(hashtags_text)
    body = truncate_body(body, max(0, available_for_body))
    final_caption = f"{body}{separator}{hashtags_text}".strip()

    if len(final_caption) > TIKTOK_DESCRIPTION_LIMIT:
        raise RuntimeError(
            f"Legenda do TikTok excedeu {TIKTOK_DESCRIPTION_LIMIT} caracteres após adaptação"
        )
    return final_caption, hashtags_text


def create_post(channel_id: str, caption: str) -> dict:
    query = f"""
    mutation CreateTikTokPost {{
      createPost(
        input: {{
          text: {gql_string(caption)}
          channelId: {gql_string(channel_id)}
          schedulingType: automatic
          mode: shareNow
          assets: [
            {{
              video: {{
                url: {gql_string(VIDEO_URL)}
                metadata: {{ thumbnailOffset: 1000 }}
              }}
            }}
          ]
        }}
      ) {{
        ... on PostActionSuccess {{
          post {{
            id
            text
            dueAt
            status
          }}
        }}
        ... on MutationError {{
          message
        }}
      }}
    }}
    """
    result = graphql(query).get("createPost", {})
    if not result.get("post"):
        raise RuntimeError(f"Buffer recusou o post: {result.get('message') or result}")
    return result["post"]


def get_post(post_id: str) -> dict:
    query = f"""
    query ConfirmTikTokPost {{
      post(input: {{ id: {gql_string(post_id)} }}) {{
        id
        status
        sentAt
        externalLink
        error {{
          message
          supportUrl
        }}
      }}
    }}
    """
    post = graphql(query).get("post")
    if not post:
        raise RuntimeError(f"Buffer não encontrou o post {post_id} para confirmação")
    return post


def wait_until_sent(post_id: str, timeout_seconds: int = 600, interval_seconds: int = 10) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() < deadline:
        post = get_post(post_id)
        status = str(post.get("status") or "unknown").lower()
        last_status = status
        save_diag(
            stage="confirm_delivery",
            post_id=post_id,
            buffer_status=status,
            sent_at=post.get("sentAt"),
            external_link=post.get("externalLink"),
        )
        if status == "sent":
            return post
        if status == "error":
            error = post.get("error") or {}
            message = error.get("message") or "erro sem mensagem"
            support_url = error.get("supportUrl") or ""
            detail = f"; suporte: {support_url}" if support_url else ""
            raise RuntimeError(f"Buffer/TikTok falhou ao publicar: {message}{detail}")
        time.sleep(interval_seconds)
    raise RuntimeError(
        f"Buffer não confirmou publicação no TikTok em {timeout_seconds // 60} minutos; "
        f"último status: {last_status}"
    )


def persist_confirmed(metadata: dict, hashtags: str, post_id: str, confirmed: dict) -> None:
    state = dict(metadata["next_state"])
    state["last_posted_at"] = confirmed.get("sentAt") or datetime.now(timezone.utc).isoformat()
    state["last_mode"] = "buffer_auto_confirmed"
    state["last_platform"] = "tiktok"
    state["last_hashtags"] = hashtags
    state["last_buffer_post_id"] = post_id
    state["last_buffer_status"] = confirmed.get("status")
    state["last_external_link"] = confirmed.get("externalLink")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_diag(
        stage="success",
        success=True,
        post_id=post_id,
        buffer_status=confirmed.get("status"),
        sent_at=confirmed.get("sentAt"),
        external_link=confirmed.get("externalLink"),
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    print(f"TikTok confirmado como publicado: {post_id}")


def pending_post_from_current_window() -> str:
    if not DIAG.exists():
        return ""
    try:
        previous = json.loads(DIAG.read_text(encoding="utf-8"))
        post_id = str(previous.get("post_id") or "").strip()
        status = str(previous.get("buffer_status") or previous.get("initial_status") or "").lower()
        stamp = previous.get("started_at") or previous.get("finished_at")
        if not post_id or status not in {"sending", "pending", "processing", "unknown"} or not stamp:
            return ""
        started = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        if started.date() == now.date() and started.hour == now.hour:
            return post_id
    except Exception:
        return ""
    return ""


def main() -> None:
    try:
        previous_post_id = pending_post_from_current_window()
        metadata = json.loads(META.read_text(encoding="utf-8"))
        caption, hashtags = adapt_caption_for_tiktok(str(metadata["caption"]))
        if previous_post_id:
            save_diag(stage="reconcile_pending", post_id=previous_post_id)
            confirmed = wait_until_sent(previous_post_id)
            persist_confirmed(metadata, hashtags, previous_post_id, confirmed)
            return

        save_diag(stage="auth", caption_length=len(caption))
        channel_id, channel_name = find_tiktok_channel()
        save_diag(stage="video_public", channel_id=channel_id, channel_name=channel_name)
        wait_public(VIDEO_URL)
        save_diag(stage="publish")
        post = create_post(channel_id, caption)
        post_id = str(post.get("id") or "").strip()
        if not post_id:
            raise RuntimeError("Buffer aceitou a criação sem retornar ID do post")

        save_diag(stage="accepted_by_buffer", post_id=post_id, initial_status=post.get("status"))
        confirmed = wait_until_sent(post_id)
        persist_confirmed(metadata, hashtags, post_id, confirmed)
    except Exception as exc:
        save_diag(
            stage=diag.get("stage", "unknown"),
            success=False,
            error_type=type(exc).__name__,
            error=str(exc)[:1800],
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
