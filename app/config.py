from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    bot_token: str = field(repr=False)  # never print the token
    owner_ids: frozenset[int]
    source_chat_id: int
    playlist_chat_id: int
    db_path: str = "/data/playlist.db"
    send_delay: float = 1.0
    max_playlist_size: int = 500
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env

        def need(name: str) -> str:
            value = env.get(name, "").strip()
            if not value:
                raise ConfigError(f"environment variable {name} is required")
            return value

        def as_int(name: str, value: str) -> int:
            try:
                return int(value)
            except ValueError:
                raise ConfigError(f"{name} must be an integer") from None

        token = need("BOT_TOKEN")
        if not _TOKEN_RE.match(token):
            raise ConfigError("BOT_TOKEN does not look like a Telegram bot token")

        owners = frozenset(
            as_int("OWNER_IDS", p.strip()) for p in need("OWNER_IDS").split(",") if p.strip()
        )
        if not owners:
            raise ConfigError("OWNER_IDS must contain at least one user id")

        source = as_int("SOURCE_CHANNEL_ID", need("SOURCE_CHANNEL_ID"))
        playlist = as_int("PLAYLIST_CHANNEL_ID", need("PLAYLIST_CHANNEL_ID"))
        if source == playlist:
            # the playlist channel is wiped on every playlist, never let it be the library
            raise ConfigError("SOURCE_CHANNEL_ID and PLAYLIST_CHANNEL_ID must be different")

        try:
            delay = float(env.get("SEND_DELAY", "1.0"))
        except ValueError:
            raise ConfigError("SEND_DELAY must be a number") from None
        if delay < 0:
            raise ConfigError("SEND_DELAY must be >= 0")

        return cls(
            bot_token=token,
            owner_ids=owners,
            source_chat_id=source,
            playlist_chat_id=playlist,
            db_path=env.get("DB_PATH", "/data/playlist.db").strip() or "/data/playlist.db",
            send_delay=delay,
            max_playlist_size=as_int("MAX_PLAYLIST_SIZE", env.get("MAX_PLAYLIST_SIZE", "500")),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
        )
