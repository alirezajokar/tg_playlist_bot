"""Wipe the playlist channel and fill it with copies of the chosen tracks."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from app.db import Database

log = logging.getLogger(__name__)

ProgressCb = Callable[[int, int], Awaitable[None]]
_MAX_CONSECUTIVE_FAILURES = 5


@dataclass
class PublishResult:
    sent: int = 0
    missing: int = 0  # source message no longer exists
    failed: int = 0
    cleared: int = 0
    clear_failed: int = 0
    cancelled: bool = False
    error: str | None = None  # fatal problem (rights / chat access)


def _is_missing_source(exc: BadRequest) -> bool:
    text = str(exc).lower()
    return "message to copy not found" in text or "message_id_invalid" in text


class PlaylistService:
    def __init__(self, db: Database, bot: Any, source_chat_id: int, playlist_chat_id: int,
                 delay: float = 1.0, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.db, self.bot = db, bot
        self.source, self.playlist = source_chat_id, playlist_chat_id
        self.delay, self._sleep = delay, sleep

    async def _call(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        """Call the API, waiting out Telegram flood limits."""
        for attempt in range(6):
            try:
                return await fn(*args, **kwargs)
            except RetryAfter as exc:
                if attempt == 5:
                    raise
                wait = exc.retry_after.total_seconds() if hasattr(exc.retry_after, "total_seconds") else exc.retry_after
                log.warning("flood limit, sleeping %.0fs", wait)
                await self._sleep(wait + 1)

    async def clear(self) -> tuple[int, int]:
        """Delete only the messages this bot posted in the playlist channel. Returns (deleted, failed)."""
        ids = self.db.playlist_message_ids()
        deleted = failed = 0
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            try:
                await self._call(self.bot.delete_messages, chat_id=self.playlist, message_ids=chunk)
                self.db.remove_playlist_items(chunk)
                deleted += len(chunk)
                continue
            except TelegramError as exc:
                log.warning("bulk delete failed (%s), deleting one by one", exc)
            for mid in chunk:  # fallback: find out exactly which ones cannot be deleted
                try:
                    await self._call(self.bot.delete_message, chat_id=self.playlist, message_id=mid)
                except BadRequest as exc:
                    if "not found" in str(exc).lower():
                        self.db.remove_playlist_items([mid])
                        deleted += 1
                    else:
                        log.warning("cannot delete %s: %s", mid, exc)
                        failed += 1
                except TelegramError as exc:
                    log.warning("cannot delete %s: %s", mid, exc)
                    failed += 1
                else:
                    self.db.remove_playlist_items([mid])
                    deleted += 1
        return deleted, failed

    async def publish(self, track_ids: Sequence[int], progress: ProgressCb | None = None,
                      cancel: asyncio.Event | None = None) -> PublishResult:
        res = PublishResult()
        res.cleared, res.clear_failed = await self.clear()
        consecutive = 0
        for n, track_id in enumerate(track_ids, 1):
            if cancel is not None and cancel.is_set():
                res.cancelled = True
                break
            try:
                copy = await self._call(
                    self.bot.copy_message,
                    chat_id=self.playlist, from_chat_id=self.source, message_id=track_id,
                )
            except BadRequest as exc:
                if _is_missing_source(exc):
                    self.db.mark_deleted(track_id)  # deleted from the channel -> forget it
                    res.missing += 1
                    consecutive = 0
                else:
                    log.warning("copy %s failed: %s", track_id, exc)
                    res.failed += 1
                    consecutive += 1
            except Forbidden as exc:
                res.error = f"{exc}"
                break
            except TelegramError as exc:
                log.warning("copy %s failed: %s", track_id, exc)
                res.failed += 1
                consecutive += 1
            else:
                self.db.add_playlist_item(copy.message_id, track_id)
                res.sent += 1
                consecutive = 0
            if consecutive >= _MAX_CONSECUTIVE_FAILURES:
                res.error = "too many consecutive failures — check the bot's access to both channels"
                break
            if progress is not None and n % 10 == 0:
                await progress(n, len(track_ids))
            await self._sleep(self.delay)
        return res
