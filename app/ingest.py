"""Turn Telegram data into `Track`s: live channel posts and Telegram Desktop JSON exports."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from app.models import Track


class ExportError(ValueError):
    """The export file is unusable (wrong channel, wrong format, ...)."""


# ---- live posts (Bot API) --------------------------------------------------
def track_from_message(msg: Any) -> Track | None:
    """Build a Track from a python-telegram-bot Message, or None if it is not music."""
    audio = getattr(msg, "audio", None)
    doc = getattr(msg, "document", None)
    if audio is not None:
        performer, title = audio.performer or "", audio.title or ""
        file_name, duration = audio.file_name or "", audio.duration
    elif doc is not None and (doc.mime_type or "").startswith("audio/"):
        performer = title = ""
        file_name, duration = doc.file_name or "", None
    else:
        return None
    return Track(
        message_id=msg.message_id,
        title=title,
        performer=performer,
        file_name=file_name,
        caption=msg.caption or "",
        duration=int(duration) if duration is not None else None,
        date=msg.date.isoformat() if getattr(msg, "date", None) else None,
    )


# ---- Telegram Desktop export (result.json) ---------------------------------
def _raw_channel_id(chat_id: int) -> int:
    """-1001234567890 (Bot API) -> 1234567890 (id used inside exports)."""
    return -chat_id - 10**12 if chat_id < -(10**12) else abs(chat_id)


def _flatten_text(text: Any) -> str:
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        return "".join(p if isinstance(p, str) else str(p.get("text", "")) for p in text)
    return ""


def _pick_chat(data: dict, source_chat_id: int) -> dict:
    raw = _raw_channel_id(source_chat_id)
    if "messages" in data:
        chats = [data]
    else:
        chats = (data.get("chats") or {}).get("list") or []
    if not chats:
        raise ExportError("no chat found in this file — export a single channel as JSON")
    matching = [c for c in chats if c.get("id") is not None and _raw_channel_id(int(c["id"])) == raw]
    if matching:
        return matching[0]
    names = ", ".join(f"{c.get('name')!r} (id {c.get('id')})" for c in chats[:5])
    raise ExportError(
        f"this export does not belong to SOURCE_CHANNEL_ID ({source_chat_id}); it contains: {names}. "
        "Message ids from another chat would copy the wrong messages, so the import was refused."
    )


def parse_export(data: Any, source_chat_id: int) -> Iterator[Track]:
    if not isinstance(data, dict):
        raise ExportError("unexpected JSON structure")
    chat = _pick_chat(data, source_chat_id)
    for m in chat.get("messages", []):
        if m.get("type") != "message":
            continue
        media = m.get("media_type")
        # music = audio_file, or an audio/* document (no media_type); voice/video notes are not music
        is_audio = media == "audio_file" or (media is None and str(m.get("mime_type", "")).startswith("audio/"))
        if not is_audio or not isinstance(m.get("id"), int):
            continue
        file_name = m.get("file_name") or ""
        if not file_name:
            f = str(m.get("file") or "")
            file_name = "" if f.startswith("(") else f.rsplit("/", 1)[-1]
        yield Track(
            message_id=m["id"],
            title=str(m.get("title") or ""),
            performer=str(m.get("performer") or ""),
            file_name=file_name,
            caption=_flatten_text(m.get("text")),
            duration=m.get("duration_seconds"),
            date=m.get("date"),
        )


def parse_export_bytes(raw: bytes | bytearray, source_chat_id: int) -> list[Track]:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ExportError("file is not valid JSON") from None
    return list(parse_export(data, source_chat_id))
