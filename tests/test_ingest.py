import json
from datetime import datetime
from types import SimpleNamespace as NS

import pytest

from app.ingest import ExportError, parse_export_bytes, track_from_message

SRC = -1001234567890


def export(chat_id=1234567890, messages=None):
    return {"name": "My music", "type": "public_channel", "id": chat_id, "messages": messages or [
        {"id": 1, "type": "service", "action": "create_channel"},
        {"id": 2, "type": "message", "text": "just text"},
        {"id": 3, "type": "message", "media_type": "audio_file", "performer": "Ebi", "title": "Shab",
         "file": "(File not included. Change data exporting settings to download.)",
         "file_name": "Ebi - Shab.mp3", "mime_type": "audio/mpeg", "duration_seconds": 200,
         "date": "2023-01-02T10:00:00",
         "text": ["nice ", {"type": "hashtag", "text": "#remix"}, " ", {"type": "hashtag", "text": "#rap"}]},
        {"id": 4, "type": "message", "media_type": "voice_message", "mime_type": "audio/ogg"},
        {"id": 5, "type": "message", "file": "files/Song.mp3", "mime_type": "audio/mpeg", "text": ""},
    ]}


def test_parse_single_channel():
    tracks = parse_export_bytes(json.dumps(export()).encode(), SRC)
    ids = [t.message_id for t in tracks]
    assert ids == [3, 5]  # service msg, plain text and voice message (id 4) are skipped
    t = next(t for t in tracks if t.message_id == 3)
    assert (t.performer, t.title, t.caption, t.duration) == ("Ebi", "Shab", "nice #remix #rap", 200)
    assert next(t for t in tracks if t.message_id == 5).file_name == "Song.mp3"


def test_parse_full_export_picks_right_chat():
    data = {"chats": {"list": [export(999, []), export()]}}
    assert len(parse_export_bytes(json.dumps(data).encode(), SRC)) >= 2


def test_wrong_channel_refused():
    with pytest.raises(ExportError, match="does not belong"):
        parse_export_bytes(json.dumps(export(chat_id=42)).encode(), SRC)


def test_bad_json():
    with pytest.raises(ExportError):
        parse_export_bytes(b"not json", SRC)
    with pytest.raises(ExportError):
        parse_export_bytes(b"[]", SRC)


def test_live_message():
    msg = NS(message_id=7, caption="#rap", date=datetime(2024, 1, 1),
             audio=NS(performer="Ebi", title="T", file_name="f.mp3", duration=100), document=None)
    t = track_from_message(msg)
    assert (t.message_id, t.performer, t.title, t.caption, t.duration) == (7, "Ebi", "T", "#rap", 100)
    doc = NS(message_id=8, caption=None, date=None, audio=None,
             document=NS(mime_type="audio/mpeg", file_name="x.mp3"))
    assert track_from_message(doc).file_name == "x.mp3"
    photo = NS(message_id=9, caption="c", date=None, audio=None, document=NS(mime_type="image/png", file_name="a"))
    assert track_from_message(photo) is None
