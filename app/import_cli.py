"""Offline import:  docker exec -it <container> python -m app.import_cli /data/result.json"""
from __future__ import annotations

import sys

from app.config import Config
from app.db import Database
from app.ingest import ExportError, parse_export_bytes


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m app.import_cli /path/to/result.json", file=sys.stderr)
        return 2
    cfg = Config.from_env()
    try:
        with open(argv[0], "rb") as fh:
            tracks = parse_export_bytes(fh.read(), cfg.source_chat_id)
    except (OSError, ExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    db = Database(cfg.db_path)
    stats = db.upsert_many(tracks, origin="import")
    db.close()
    print(f"{len(tracks)} music posts found: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
