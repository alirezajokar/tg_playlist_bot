from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone

from app.models import Track
from app.search import Clause, build_where
from app.textutil import extract_hashtags, norm, pad

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    message_id INTEGER PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '',
    performer  TEXT NOT NULL DEFAULT '',
    file_name  TEXT NOT NULL DEFAULT '',
    caption    TEXT NOT NULL DEFAULT '',
    duration   INTEGER,
    date       TEXT,
    n_artist   TEXT NOT NULL,
    n_title    TEXT NOT NULL,
    n_all      TEXT NOT NULL,
    origin     TEXT NOT NULL DEFAULT 'live',   -- 'live' (bot saw it) | 'import' (desktop export)
    deleted    INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS track_tags (
    message_id INTEGER NOT NULL REFERENCES tracks(message_id) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (message_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_track_tags_tag ON track_tags(tag);
CREATE TABLE IF NOT EXISTS playlist_items (       -- copies the bot posted in the playlist channel
    copy_message_id INTEGER PRIMARY KEY,
    track_id        INTEGER NOT NULL,
    sent_at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# Future schema changes: append (version, sql) here; they run in order on startup.
_MIGRATIONS: list[tuple[int, str]] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalized(t: Track) -> tuple[str, str, str]:
    n_all = norm(" ".join((t.performer, t.title, t.file_name, t.caption)))
    return pad(norm(t.performer)), pad(norm(t.title)), pad(n_all)


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(_SCHEMA)
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for target, sql in _MIGRATIONS:
            if version < target:
                self.conn.executescript(sql)
                version = target
        self.conn.execute(f"PRAGMA user_version = {max(version, SCHEMA_VERSION)}")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---- tracks -------------------------------------------------------------
    def _upsert(self, t: Track, origin: str) -> str:
        row = self.conn.execute("SELECT * FROM tracks WHERE message_id = ?", (t.message_id,)).fetchone()
        n_artist, n_title, n_all = _normalized(t)
        if row is None:
            self.conn.execute(
                "INSERT INTO tracks (message_id, title, performer, file_name, caption, duration, date,"
                " n_artist, n_title, n_all, origin, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.message_id, t.title, t.performer, t.file_name, t.caption, t.duration, t.date,
                 n_artist, n_title, n_all, origin, _now()),
            )
            status = "inserted"
        else:
            if origin == "import" and row["origin"] == "live":
                return "skipped"  # live data is newer than an export
            same = (row["title"], row["performer"], row["file_name"], row["caption"]) == (
                t.title, t.performer, t.file_name, t.caption)
            if same and not row["deleted"]:
                if origin == "live" and row["origin"] != "live":
                    self.conn.execute("UPDATE tracks SET origin='live' WHERE message_id=?", (t.message_id,))
                return "unchanged"
            self.conn.execute(
                "UPDATE tracks SET title=?, performer=?, file_name=?, caption=?, duration=?, date=COALESCE(?, date),"
                " n_artist=?, n_title=?, n_all=?, origin=?, deleted=0, updated_at=? WHERE message_id=?",
                (t.title, t.performer, t.file_name, t.caption, t.duration, t.date,
                 n_artist, n_title, n_all, origin, _now(), t.message_id),
            )
            status = "updated"
        self.conn.execute("DELETE FROM track_tags WHERE message_id = ?", (t.message_id,))
        self.conn.executemany(
            "INSERT INTO track_tags (message_id, tag) VALUES (?, ?)",
            [(t.message_id, tag) for tag in extract_hashtags(t.caption)],
        )
        return status

    def upsert_track(self, track: Track, origin: str = "live") -> str:
        """Returns 'inserted' | 'updated' | 'unchanged' | 'skipped'."""
        with self.conn:
            return self._upsert(track, origin)

    def upsert_many(self, tracks: Iterable[Track], origin: str = "import") -> dict[str, int]:
        stats = {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        with self.conn:  # one transaction
            for t in tracks:
                stats[self._upsert(t, origin)] += 1
        return stats

    def mark_deleted(self, message_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE tracks SET deleted=1, updated_at=? WHERE message_id=?", (_now(), message_id))

    def find(self, clauses: list[Clause], limit: int | None = None) -> list[Track]:
        where, params = build_where(clauses)
        sql = (
            "SELECT t.*, (SELECT group_concat(tag, ' ') FROM track_tags g WHERE g.message_id = t.message_id) AS tags"
            f" FROM tracks t WHERE t.deleted = 0 AND {where} ORDER BY t.message_id"
        )
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [
            Track(
                message_id=r["message_id"], title=r["title"], performer=r["performer"],
                file_name=r["file_name"], caption=r["caption"], duration=r["duration"], date=r["date"],
                tags=tuple((r["tags"] or "").split()),
            )
            for r in self.conn.execute(sql, params)
        ]

    # ---- stats --------------------------------------------------------------
    def tag_counts(self, limit: int = 40) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            "SELECT g.tag, COUNT(*) c FROM track_tags g JOIN tracks t USING (message_id)"
            " WHERE t.deleted = 0 GROUP BY g.tag ORDER BY c DESC, g.tag LIMIT ?", (limit,))
        return [(r[0], r[1]) for r in rows]

    def artist_counts(self, limit: int = 40) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            "SELECT MIN(performer), COUNT(*) c FROM tracks WHERE deleted = 0 AND performer != ''"
            " GROUP BY n_artist ORDER BY c DESC, n_artist LIMIT ?", (limit,))
        return [(r[0], r[1]) for r in rows]

    def stats(self) -> dict[str, int]:
        q = self.conn.execute
        return {
            "tracks": q("SELECT COUNT(*) FROM tracks WHERE deleted = 0").fetchone()[0],
            "deleted": q("SELECT COUNT(*) FROM tracks WHERE deleted = 1").fetchone()[0],
            "tags": q("SELECT COUNT(DISTINCT tag) FROM track_tags").fetchone()[0],
            "in_playlist": q("SELECT COUNT(*) FROM playlist_items").fetchone()[0],
        }

    # ---- playlist bookkeeping ----------------------------------------------
    def add_playlist_item(self, copy_message_id: int, track_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO playlist_items VALUES (?, ?, ?)", (copy_message_id, track_id, _now()))

    def playlist_message_ids(self) -> list[int]:
        return [r[0] for r in self.conn.execute("SELECT copy_message_id FROM playlist_items ORDER BY 1")]

    def remove_playlist_items(self, ids: Sequence[int]) -> None:
        with self.conn:
            self.conn.executemany("DELETE FROM playlist_items WHERE copy_message_id = ?", [(i,) for i in ids])

    # ---- meta ---------------------------------------------------------------
    def set_meta(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))

    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None
