from __future__ import annotations

import logging
import re
import sys

from app.bot import ALLOWED_UPDATES, PlaylistBot
from app.config import Config, ConfigError
from app.db import Database

_TOKEN_IN_TEXT = re.compile(r"(bot)?\d{6,}:[A-Za-z0-9_-]{20,}")


class RedactingFormatter(logging.Formatter):
    """Bot API URLs contain the token; make sure it never reaches the logs."""

    def format(self, record: logging.LogRecord) -> str:
        return _TOKEN_IN_TEXT.sub("<redacted-token>", super().format(record))


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
    for noisy in ("httpx", "httpcore", "telegram.ext"):
        logging.getLogger(noisy).setLevel(logging.WARNING)  # httpx logs full URLs at INFO


def main() -> None:
    try:
        cfg = Config.from_env()
    except ConfigError as exc:
        sys.exit(f"configuration error: {exc}")
    setup_logging(cfg.log_level)
    db = Database(cfg.db_path)
    app = PlaylistBot(cfg, db).build()
    logging.getLogger(__name__).info("starting (long polling, no inbound ports)")
    app.run_polling(allowed_updates=ALLOWED_UPDATES)


if __name__ == "__main__":
    main()
