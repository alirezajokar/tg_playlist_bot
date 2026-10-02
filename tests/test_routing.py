"""Handler routing/authorisation without touching the network."""
from datetime import datetime

from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import CallbackQueryHandler, MessageHandler

from app.bot import PlaylistBot
from app.config import Config

CFG = Config.from_env({"BOT_TOKEN": "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "OWNER_IDS": "7",
                       "SOURCE_CHANNEL_ID": "-1001", "PLAYLIST_CHANNEL_ID": "-1002"})


def handlers_for(db, update):
    app = PlaylistBot(CFG, db).build()
    return [h.callback.__name__ for h in app.handlers[0] if h.check_update(update)]


def private(user_id, text):
    entities = [MessageEntity("bot_command", 0, len(text))] if text.startswith("/") else None
    msg = Message(1, datetime.now(), Chat(user_id, "private"), from_user=User(user_id, "x", False),
                  text=text, entities=entities)
    bot = Bot(CFG.bot_token)
    bot._bot_user = User(99, "b", True, username="testbot")  # avoids the get_me() network call
    msg.set_bot(bot)
    return Update(1, message=msg)


def channel(chat_id, edited=False):
    msg = Message(5, datetime.now(), Chat(chat_id, "channel"), text="x")
    return Update(1, edited_channel_post=msg) if edited else Update(1, channel_post=msg)


def test_owner_text_is_search(db):
    assert handlers_for(db, private(7, "ebi")) == ["on_query"]


def test_stranger_is_ignored(db):
    assert handlers_for(db, private(8, "ebi")) == []
    assert handlers_for(db, private(8, "/clear")) == []


def test_owner_command(db):
    assert handlers_for(db, private(7, "/clear")) == ["cmd_clear"]


def test_channel_posts_only_from_source(db):
    assert handlers_for(db, channel(-1001)) == ["on_source_post"]
    assert handlers_for(db, channel(-1001, edited=True)) == ["on_source_post"]
    assert handlers_for(db, channel(-1002)) == []  # playlist channel is never ingested
    assert handlers_for(db, channel(-1999)) == []
