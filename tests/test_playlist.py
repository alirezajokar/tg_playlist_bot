import asyncio
from types import SimpleNamespace as NS

from telegram.error import BadRequest, Forbidden, RetryAfter

from app.models import Track
from app.playlist import PlaylistService

SRC, PL = -1001, -1002


class FakeBot:
    def __init__(self, missing=(), flood_once=False, forbidden=False, undeletable=()):
        self.channel: dict[int, int] = {}  # copy id -> source id
        self.next_id = 100
        self.missing, self.flood_once, self.forbidden = set(missing), flood_once, forbidden
        self.undeletable = set(undeletable)
        self.sources: list[int] = []

    async def copy_message(self, chat_id, from_chat_id, message_id):
        assert (chat_id, from_chat_id) == (PL, SRC)  # never copies into the library
        if self.forbidden:
            raise Forbidden("bot is not a member")
        if self.flood_once:
            self.flood_once = False
            raise RetryAfter(3)
        if message_id in self.missing:
            raise BadRequest("message to copy not found")
        self.next_id += 1
        self.channel[self.next_id] = message_id
        self.sources.append(message_id)
        return NS(message_id=self.next_id)

    async def delete_messages(self, chat_id, message_ids):
        assert chat_id == PL
        if self.undeletable & set(message_ids):
            raise BadRequest("message can't be deleted")
        for m in message_ids:
            self.channel.pop(m, None)
        return True

    async def delete_message(self, chat_id, message_id):
        assert chat_id == PL
        if message_id in self.undeletable:
            raise BadRequest("message can't be deleted")
        if message_id not in self.channel:
            raise BadRequest("message to delete not found")
        del self.channel[message_id]
        return True


def make(db, bot, delay=0):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    return PlaylistService(db, bot, SRC, PL, delay=delay, sleep=fake_sleep), sleeps


def seed(db, n=5):
    db.upsert_many([Track(i, title=f"t{i}") for i in range(1, n + 1)])


def test_publish_replaces_previous_playlist(db):
    seed(db)
    bot = FakeBot()
    svc, _ = make(db, bot)
    r1 = asyncio.run(svc.publish([1, 2, 3]))
    assert r1.sent == 3 and sorted(bot.channel.values()) == [1, 2, 3]
    r2 = asyncio.run(svc.publish([4, 5]))
    assert r2.sent == 2 and r2.cleared == 3
    assert sorted(bot.channel.values()) == [4, 5]  # old ones gone, order preserved
    assert db.stats()["in_playlist"] == 2


def test_order_preserved(db):
    seed(db)
    bot = FakeBot()
    svc, _ = make(db, bot)
    asyncio.run(svc.publish([3, 1, 2]))
    assert bot.sources == [3, 1, 2]


def test_missing_source_is_forgotten(db):
    seed(db)
    bot = FakeBot(missing={2})
    svc, _ = make(db, bot)
    r = asyncio.run(svc.publish([1, 2, 3]))
    assert (r.sent, r.missing, r.failed) == (2, 1, 0)
    assert db.stats()["tracks"] == 4 and db.stats()["deleted"] == 1


def test_flood_wait_is_waited_out(db):
    seed(db)
    bot = FakeBot(flood_once=True)
    svc, sleeps = make(db, bot)
    r = asyncio.run(svc.publish([1, 2]))
    assert r.sent == 2 and 4 in sleeps  # RetryAfter(3) + 1


def test_forbidden_aborts(db):
    seed(db)
    svc, _ = make(db, FakeBot(forbidden=True))
    r = asyncio.run(svc.publish([1, 2, 3]))
    assert r.sent == 0 and r.error


def test_cancel(db):
    seed(db)
    svc, _ = make(db, FakeBot())
    ev = asyncio.Event()
    ev.set()
    r = asyncio.run(svc.publish([1, 2], cancel=ev))
    assert r.cancelled and r.sent == 0


def test_undeletable_is_reported_and_kept(db):
    seed(db)
    bot = FakeBot()
    svc, _ = make(db, bot)
    asyncio.run(svc.publish([1, 2]))
    stuck = next(iter(bot.channel))
    bot.undeletable = {stuck}
    r = asyncio.run(svc.publish([3]))
    assert r.clear_failed == 1 and r.cleared == 1
    assert db.stats()["in_playlist"] == 2  # the stuck copy stays tracked + the new one


def test_clear_only_touches_tracked_messages(db):
    seed(db)
    bot = FakeBot()
    bot.channel[999] = -1  # a message the bot did not post (not tracked)
    svc, _ = make(db, bot)
    asyncio.run(svc.publish([1]))
    asyncio.run(svc.clear())
    assert 999 in bot.channel and len(bot.channel) == 1
