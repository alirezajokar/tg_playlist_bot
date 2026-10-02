from __future__ import annotations

import asyncio
import html
import json
import logging
import secrets
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from app import texts
from app.config import Config
from app.db import Database
from app.ingest import ExportError, parse_export_bytes, track_from_message
from app.models import Track
from app.playlist import PlaylistService, PublishResult
from app.search import parse_query

log = logging.getLogger(__name__)

PAGE_SIZE = 15
MAX_PENDING = 20
MAX_IMPORT_BYTES = 20 * 1024 * 1024  # Bot API download limit
ALLOWED_UPDATES = ["message", "callback_query", "channel_post", "edited_channel_post"]


def esc(text: str) -> str:
    return html.escape(text, quote=False)


@dataclass
class Pending:
    query: str
    tracks: list[Track]


class PlaylistBot:
    def __init__(self, cfg: Config, db: Database):
        self.cfg, self.db = cfg, db
        self.pending: OrderedDict[str, Pending] = OrderedDict()
        self.lock = asyncio.Lock()  # one playlist build at a time
        self.cancel = asyncio.Event()

    # ---- wiring -------------------------------------------------------------
    def build(self) -> Application:
        app = Application.builder().token(self.cfg.bot_token).post_init(self.post_init).build()
        owner = filters.ChatType.PRIVATE & filters.User(user_id=list(self.cfg.owner_ids))
        source = filters.Chat(chat_id=self.cfg.source_chat_id) & filters.UpdateType.CHANNEL_POSTS

        app.add_handler(MessageHandler(source, self.on_source_post))
        for name, fn in {
            "start": self.cmd_help, "help": self.cmd_help, "import": self.cmd_import_help,
            "stats": self.cmd_stats, "tags": self.cmd_tags, "artists": self.cmd_artists,
            "status": self.cmd_status, "clear": self.cmd_clear, "stop": self.cmd_stop,
        }.items():
            app.add_handler(CommandHandler(name, fn, filters=owner))
        app.add_handler(MessageHandler(owner & filters.Document.ALL, self.on_document))
        app.add_handler(MessageHandler(owner & filters.TEXT & ~filters.COMMAND, self.on_query))
        app.add_handler(CallbackQueryHandler(self.on_callback, pattern=r"^p:"))
        app.add_error_handler(self.on_error)
        return app

    async def post_init(self, app: Application) -> None:
        for line in await self.check_access(app.bot):
            log.info("access check: %s", line)

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("unhandled error", exc_info=context.error)

    # ---- channel ingestion ----------------------------------------------------
    async def on_source_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        track = track_from_message(msg) if msg else None
        if track is None:
            return
        status = self.db.upsert_track(track, origin="live")
        log.info("source post %s: %s", track.message_id, status)

    # ---- search ---------------------------------------------------------------
    async def on_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text
        clauses = parse_query(text)
        if not clauses:
            await update.message.reply_text(texts.EMPTY_QUERY)
            return
        tracks = self.db.find(clauses)
        if not tracks:
            await update.message.reply_text(texts.NOT_FOUND)
            return
        token = secrets.token_hex(4)
        self.pending[token] = Pending(text, tracks)
        while len(self.pending) > MAX_PENDING:
            self.pending.popitem(last=False)
        body, markup = self.render(token, 0)
        await update.message.reply_text(body, reply_markup=markup, parse_mode=ParseMode.HTML)

    def render(self, token: str, page: int) -> tuple[str, InlineKeyboardMarkup]:
        p = self.pending[token]
        pages = (len(p.tracks) + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        lines = []
        for i, t in enumerate(p.tracks[start:start + PAGE_SIZE], start + 1):
            tags = " ".join(f"#{x}" for x in t.tags[:3])
            lines.append(f"{i}. {esc(t.label[:70])} <i>{esc(tags)}</i>".rstrip())
        body = f"🔎 <b>{esc(p.query[:100])}</b> — {len(p.tracks)} موزیک\n\n" + "\n".join(lines)
        cb = lambda action: f"p:{token}:{action}"  # noqa: E731
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️", callback_data=cb(f"n{page - 1}")))
        nav.append(InlineKeyboardButton(f"{page + 1}/{pages}", callback_data=cb("noop")))
        if page < pages - 1:
            nav.append(InlineKeyboardButton("▶️", callback_data=cb(f"n{page + 1}")))
        markup = InlineKeyboardMarkup([
            nav,
            [InlineKeyboardButton(f"📤 ساخت پلی‌لیست ({len(p.tracks)})", callback_data=cb("go")),
             InlineKeyboardButton("✖️ لغو", callback_data=cb("x"))],
        ])
        return body, markup

    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        if q.from_user.id not in self.cfg.owner_ids:
            await q.answer()
            return
        _, token, action = q.data.split(":", 2)
        p = self.pending.get(token)
        if p is None:
            await q.answer(texts.EXPIRED, show_alert=True)
            return
        if action == "noop":
            await q.answer()
        elif action == "x":
            self.pending.pop(token, None)
            await q.answer()
            await q.edit_message_text("لغو شد.")
        elif action.startswith("n") and action[1:].isdigit():
            body, markup = self.render(token, int(action[1:]))
            await q.answer()
            await self._edit(q, body, markup)
        elif action == "go":
            if self.lock.locked():
                await q.answer(texts.BUSY, show_alert=True)
                return
            if len(p.tracks) > self.cfg.max_playlist_size:
                await q.answer(texts.TOO_MANY.format(n=len(p.tracks), max=self.cfg.max_playlist_size),
                               show_alert=True)
                return
            await q.answer()
            self.pending.pop(token, None)
            await q.edit_message_text("⏳ در حال پاک کردن پلی‌لیست قبلی و ساخت پلی‌لیست جدید…")
            context.application.create_task(self.run_publish(q.message, p))

    @staticmethod
    async def _edit(q, body: str, markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await q.edit_message_text(body, reply_markup=markup, parse_mode=ParseMode.HTML)
        except BadRequest as exc:
            if "not modified" not in str(exc).lower():
                raise

    # ---- playlist build ---------------------------------------------------------
    def service(self, bot) -> PlaylistService:
        return PlaylistService(self.db, bot, self.cfg.source_chat_id, self.cfg.playlist_chat_id,
                               delay=self.cfg.send_delay)

    async def run_publish(self, status_msg, p: Pending) -> None:
        async with self.lock:
            self.cancel.clear()

            async def progress(done: int, total: int) -> None:
                try:
                    await status_msg.edit_text(f"⏳ {done} / {total} ارسال شد…")
                except TelegramError:
                    pass

            try:
                res = await self.service(status_msg.get_bot()).publish(
                    [t.message_id for t in p.tracks], progress=progress, cancel=self.cancel)
            except Exception:
                log.exception("publish crashed")
                await status_msg.edit_text("❌ خطای غیرمنتظره؛ لاگ سرور رو ببین.")
                return
            self.db.set_meta("last_query", p.query)
            self.db.set_meta("last_publish_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            await status_msg.edit_text(self.summary(p.query, res), parse_mode=ParseMode.HTML)

    @staticmethod
    def summary(query: str, r: PublishResult) -> str:
        head = "⏹ متوقف شد" if r.cancelled else "❌ ناقص موند" if r.error else "✅ پلی‌لیست آماده‌ست"
        lines = [f"{head}: <b>{esc(query[:100])}</b>", f"ارسال‌شده: {r.sent}"]
        if r.cleared:
            lines.append(f"از پلی‌لیست قبلی پاک شد: {r.cleared}")
        if r.clear_failed:
            lines.append(f"⚠️ {r.clear_failed} پیام قبلی پاک نشد (دسترسی Delete messages رو چک کن)")
        if r.missing:
            lines.append(f"⚠️ {r.missing} موزیک دیگه تو کانال اصلی نیست و از دیتابیس حذف شد")
        if r.failed:
            lines.append(f"⚠️ ارسال {r.failed} موزیک ناموفق بود")
        if r.error:
            lines.append(f"خطا: {esc(r.error)}")
        return "\n".join(lines)

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self.lock.locked():
            self.cancel.set()
            await update.message.reply_text(texts.STOPPING)
        else:
            await update.message.reply_text(texts.NOTHING_RUNNING)

    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self.lock.locked():
            await update.message.reply_text(texts.BUSY)
            return
        async with self.lock:
            deleted, failed = await self.service(context.bot).clear()
        extra = f"\n⚠️ {failed} پیام پاک نشد (دسترسی Delete messages؟)" if failed else ""
        await update.message.reply_text(f"🧹 {deleted} پیام از کانال پلی‌لیست پاک شد.{extra}")

    # ---- info commands ----------------------------------------------------------
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(texts.HELP, parse_mode=ParseMode.HTML)

    async def cmd_import_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(texts.IMPORT_HELP, parse_mode=ParseMode.HTML)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        s = self.db.stats()
        last = self.db.get_meta("last_query")
        text = (f"🎼 موزیک: {s['tracks']}\n🏷 هشتگ: {s['tags']}\n"
                f"🗑 حذف‌شده از کانال: {s['deleted']}\n📻 الان تو پلی‌لیست: {s['in_playlist']}")
        if last:
            text += f"\nآخرین پلی‌لیست: {esc(last[:100])}"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def cmd_tags(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = self.db.tag_counts(60)
        text = "\n".join(f"#{esc(t)} — {c}" for t, c in rows) or "هنوز هشتگی ثبت نشده."
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def cmd_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = self.db.artist_counts(60)
        text = "\n".join(f"{esc(a)} — {c}" for a, c in rows) or "هنوز خواننده‌ای ثبت نشده."
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def check_access(self, bot) -> list[str]:
        """Human-readable report of the bot's rights in both channels."""
        report = []
        for label, chat_id, need in (
            ("کانال اصلی", self.cfg.source_chat_id, ()),
            ("کانال پلی‌لیست", self.cfg.playlist_chat_id, ("can_post_messages", "can_delete_messages")),
        ):
            try:
                chat = await bot.get_chat(chat_id)
                member = await bot.get_chat_member(chat_id, bot.id)
            except TelegramError as exc:
                report.append(f"❌ {label}: دسترسی ندارم ({exc})")
                continue
            if member.status != "administrator":
                report.append(f"❌ {label} «{chat.title}»: بات باید ادمین باشه (الان: {member.status})")
                continue
            missing = [r for r in need if not getattr(member, r, False)]
            if missing:
                report.append(f"⚠️ {label} «{chat.title}»: ادمینه ولی این دسترسی‌ها رو نداره: {', '.join(missing)}")
            else:
                report.append(f"✅ {label} «{chat.title}»: OK")
        return report

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("\n".join(await self.check_access(context.bot)))

    # ---- import -----------------------------------------------------------------
    async def on_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        doc = update.message.document
        if not (doc.file_name or "").lower().endswith(".json"):
            await update.message.reply_text(texts.IMPORT_NOT_JSON, parse_mode=ParseMode.HTML)
            return
        if (doc.file_size or 0) > MAX_IMPORT_BYTES:
            await update.message.reply_text(texts.IMPORT_TOO_BIG)
            return
        raw = await (await doc.get_file()).download_as_bytearray()
        try:
            tracks = await asyncio.to_thread(parse_export_bytes, raw, self.cfg.source_chat_id)
        except (ExportError, json.JSONDecodeError) as exc:
            await update.message.reply_text(f"❌ {exc}")
            return
        stats = self.db.upsert_many(tracks, origin="import")
        await update.message.reply_text(
            f"✅ {len(tracks)} موزیک تو فایل بود\n"
            f"جدید: {stats['inserted']} · آپدیت: {stats['updated']} · بدون تغییر: {stats['unchanged']}"
            + (f" · نادیده (جدیدتر از خود بات): {stats['skipped']}" if stats["skipped"] else ""))
