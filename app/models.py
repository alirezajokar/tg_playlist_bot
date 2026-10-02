from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Track:
    """A music post in the source channel. `message_id` is its id inside that channel."""

    message_id: int
    title: str = ""
    performer: str = ""
    file_name: str = ""
    caption: str = ""
    duration: int | None = None
    date: str | None = None
    tags: tuple[str, ...] = ()  # filled from the DB when loading

    @property
    def label(self) -> str:
        if self.performer and self.title:
            return f"{self.performer} – {self.title}"
        stem = self.file_name.rsplit(".", 1)[0] if self.file_name else ""
        return self.title or self.performer or stem or f"#{self.message_id}"
