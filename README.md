# Telegram Music Channel Playlist Bot

**Search your own Telegram music channel by artist, title or hashtag — and turn the results into a playlist channel with one tap.**

[![CI](https://github.com/alirezajokar/tg_playlist_bot/actions/workflows/ci.yml/badge.svg)](https://github.com/alirezajokar/tg_playlist_bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)

🇬🇧 [English](#english) · 🇮🇷 [فارسی](#فارسی)

---

## English

### What is this?

You keep your favourite songs in a Telegram channel. Telegram search can *find* a song, but it cannot say
*"play only the tracks by this artist"* or *"only the ones I tagged `#remix` and `#rap`"*.

**tg_playlist_bot** is a self-hosted Telegram bot that reads the music posts of your channel
(artist, title, file name, caption, **hashtags**), keeps them searchable, and when you ask for
`ebi` or `#remix -#rap` it **copies all matching tracks into a separate, empty "playlist" channel**.
Next time, it wipes that channel and builds a fresh playlist. Open the playlist channel in Telegram and press play.

Use it to:

* 🎤 play every song of one artist from a big music channel
* 🏷️ build playlists from hashtags (`#remix`, `#rap`, `#workout`, `#پاپ_ایرانی` …)
* 🔎 search a Telegram music library by artist **and** title **and** hashtag at the same time
* 🧹 keep a throw-away "now playing" channel that is rebuilt on demand

### Features

* **Powerful search** — word-prefix match across artist, title, file name, caption and hashtags; exact `#hashtag`
  filters; exclusions (`-#remix`); field filters (`artist:`, `title:`); `"exact phrases"`. All terms are AND-ed.
* **Persian + English friendly** — case-insensitive, normalises `ي/ی`, `ك/ک`, Persian/Arabic digits, ZWNJ and diacritics.
* **Stays up to date** — new tracks and **edited captions/hashtags** in your channel are picked up automatically.
* **Import your existing library** — Telegram bots cannot read old channel history, so you import a
  Telegram Desktop **JSON** export once (send the file to the bot, or use the CLI).
* **No downloading, no re-uploading** — tracks are copied with Telegram's `copyMessage` (no "forwarded from" label, no bandwidth cost).
* **Safe playlist rebuilds** — the bot deletes *only* the messages it posted itself in the playlist channel,
  respects Telegram flood limits, can be stopped with `/stop`, and forgets tracks you deleted from the source channel.
* **Private by design** — only the owner(s) can use the bot; no web server, no open ports (long polling).
* **Easy to deploy** — one `docker compose up`; works great on [Dokploy](https://dokploy.com), Coolify, Portainer or any VPS.
* **Easy to extend** — small, tested Python codebase (python-telegram-bot + SQLite), no heavy framework.

### How it works

```
Source channel ──(new / edited posts)──▶ bot ──▶ SQLite (artist, title, hashtags)
                                          │
 You, in a private chat:  "ebi -#remix" ─▶ preview ─▶ [📤 Build playlist]
                                          │   1) delete the bot's previous copies
 Playlist channel ◀──── copyMessage ◀─────┘   2) copy every match, in order
```

### Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token. (Optional but recommended: `/setjoingroups` → Disable.)
2. Create an **empty playlist channel**. Add the bot as admin to **both** channels:
   * source channel — admin, no extra rights needed (it receives posts and copies from it)
   * playlist channel — admin with **Post messages** and **Delete messages**
3. Find your numeric user id ([@userinfobot](https://t.me/userinfobot)) and both channel ids (`-100…`, e.g. via [@RawDataBot](https://t.me/RawDataBot)).
4. Configure and run:

   ```bash
   git clone https://github.com/alirezajokar/tg_playlist_bot.git
   cd tg_playlist_bot
   cp .env.example .env      # fill in BOT_TOKEN, OWNER_IDS, SOURCE_CHANNEL_ID, PLAYLIST_CHANNEL_ID
   docker compose --env-file .env up -d --build
   ```

   On **Dokploy**: create a *Docker Compose* project from this repo and set the four variables in the Environment tab.
   The database lives in the `bot_data` volume and survives redeploys.
5. In a private chat with the bot send `/status` — it checks its rights in both channels.

### Import your existing songs

In **Telegram Desktop**: open the channel → ⋮ → **Export chat history** → untick all media →
set **Format: JSON** (not HTML!) → Export. Then either:

* send `result.json` to the bot in the private chat (limit: 20 MB — plenty for thousands of tracks without media), or
* `docker cp result.json <container>:/tmp/result.json && docker exec <container> python -m app.import_cli /tmp/result.json`

Only music posts are imported (text, photos, videos, voice messages are ignored). The import is idempotent,
never overwrites newer live data, and refuses an export that belongs to a different channel.

### Search syntax

Send any text to the bot in a private chat:

| You send | Meaning |
|---|---|
| `ebi` | tracks where a word starts with `ebi` in artist / title / file name / caption / hashtags (`Rebirth` does **not** match) |
| `#remix` | exact hashtag `#remix` |
| `#remix #rap` | both hashtags |
| `ebi -#remix` | `ebi`, but not remixes |
| `artist:ebi` · `title:shab` | only in the artist / only in the title |
| `"shab bokhor"` | exact phrase |

Commands: `/tags` `/artists` `/stats` `/status` `/clear` `/stop` `/import` `/help`.

### Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | | Token from @BotFather |
| `OWNER_IDS` | ✅ | | Comma-separated Telegram user ids allowed to use the bot |
| `SOURCE_CHANNEL_ID` | ✅ | | Channel that holds your music (`-100…`) |
| `PLAYLIST_CHANNEL_ID` | ✅ | | Empty channel where playlists are built (must differ from the source) |
| `DB_PATH` | | `/data/playlist.db` | SQLite file |
| `SEND_DELAY` | | `1.0` | Seconds between two copied tracks (flood-limit friendly) |
| `MAX_PLAYLIST_SIZE` | | `500` | Maximum tracks per playlist |
| `LOG_LEVEL` | | `INFO` | Python log level |

### Security

* **Owner-only:** messages and button presses from anyone not in `OWNER_IDS` are ignored.
* Only posts from `SOURCE_CHANNEL_ID` are indexed; the bot refuses to start if source and playlist channels are the same.
* The bot deletes only message ids it recorded as its own copies — never anything in the source channel.
* The token is never printed (httpx URL logging is off and every log line is redacted).
* All SQL is parameterised; user/channel text is HTML-escaped before display; imports are size-limited JSON parsing only.
* The container runs as non-root with a read-only filesystem, no capabilities, no published ports.
* Found something? See [SECURITY.md](SECURITY.md).

### FAQ

**Can the bot read my old channel messages by itself?** No — Telegram's Bot API does not allow bots to read channel history. That is why the one-time JSON import exists. After that everything is automatic.

**Why copy instead of forward?** Copies have no "forwarded from" header and keep the original audio, caption and hashtags.

**Does it detect that I deleted a song?** Telegram does not notify bots about deletions. The bot notices when it tries to copy a missing track and removes it from its database.

**Can many people share one bot?** Not at the moment — it is deliberately a single-owner tool (one library, one playlist channel). Everyone can run their own instance in minutes.

**Is it legal to make my playlist channel public?** The bot only copies your own channel's posts, but sharing copyrighted music publicly is your responsibility.

### Roadmap ideas (contributions welcome)

Shuffle / newest-first ordering · artist aliases (`ebi` ⇄ `ابی`) · HTML-export importer · `/random N` · more UI languages · multiple playlist channels.

### Contributing

Issues and pull requests are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

### License

[MIT](LICENSE)

---

<div dir="rtl">

## فارسی

### این پروژه چیه؟

موزیک‌های مورد علاقه‌ات رو توی یک کانال تلگرام نگه می‌داری. جست‌وجوی تلگرام می‌تونه آهنگ رو *پیدا* کنه، ولی نمی‌تونه بگه
«فقط آهنگ‌های این خواننده رو پلی کن» یا «فقط اونایی که هشتگ `#remix` و `#rap` دارن».

**tg_playlist_bot** یک بات تلگرام **خودمیزبان (self-hosted)** و متن‌باز هست که پست‌های موزیک کانالت رو
(اسم خواننده، اسم آهنگ، اسم فایل، کپشن و **هشتگ‌ها**) می‌خونه و قابل جست‌وجو نگه می‌داره. وقتی بهش می‌گی
`ebi` یا `#remix -#rap`، **همه‌ی آهنگ‌های مطابق رو توی یک کانال خالی جدا («کانال پلی‌لیست») کپی می‌کنه**.
دفعه‌ی بعد اون کانال رو خالی می‌کنه و پلی‌لیست جدید می‌سازه. کانال پلی‌لیست رو توی تلگرام باز کن و پلی بزن.

به درد این کارها می‌خوره:

* 🎤 پخش همه‌ی آهنگ‌های یک خواننده از یک کانال موزیک بزرگ
* 🏷️ ساخت پلی‌لیست از روی هشتگ (`#remix`، `#rap`، `#ورزش`، `#پاپ_ایرانی` …)
* 🔎 جست‌وجوی هم‌زمان در اسم خواننده، اسم آهنگ و هشتگ‌ها در کتابخونه‌ی موزیک تلگرام
* 🧹 یک کانال «در حال پخش» موقت که هر وقت بخوای از نو ساخته می‌شه

### امکانات

* **جست‌وجوی قدرتمند** — تطبیق اول‌کلمه روی خواننده، آهنگ، اسم فایل، کپشن و هشتگ؛ فیلتر دقیق `#هشتگ`؛ حذف با `-`؛ فیلتر فیلد (`artist:` و `title:`)؛ عبارت دقیق با `"..."`؛ همه‌ی شرط‌ها با «و» ترکیب می‌شن.
* **مناسب فارسی و انگلیسی** — بدون حساسیت به بزرگ/کوچک، یکسان‌سازی `ي/ی` و `ك/ک`، اعداد فارسی/عربی، نیم‌فاصله و اعراب.
* **همیشه به‌روز** — آهنگ جدید و **ویرایش کپشن/هشتگ** خودکار شناسایی می‌شه.
* **ایمپورت کتابخونه‌ی فعلی** — بات‌های تلگرام نمی‌تونن تاریخچه‌ی کانال رو بخونن؛ پس یک بار اکسپورت **JSON** تلگرام دسکتاپ رو وارد می‌کنی (فایل رو برای بات بفرست یا از CLI استفاده کن).
* **بدون دانلود و آپلود دوباره** — آهنگ‌ها با `copyMessage` تلگرام کپی می‌شن (بدون برچسب «forwarded from» و بدون مصرف ترافیک سرور).
* **بازسازی امن پلی‌لیست** — فقط پیام‌هایی پاک می‌شن که خود بات فرستاده، محدودیت ارسال تلگرام رعایت می‌شه، با `/stop` متوقف می‌شه و آهنگ‌های حذف‌شده از کانال اصلی از دیتابیس پاک می‌شن.
* **خصوصی** — فقط مالک (یا مالک‌ها) می‌تونن از بات استفاده کنن؛ بدون وب‌سرور و بدون پورت باز (long polling).
* **راه‌اندازی آسان** — یک `docker compose up`؛ روی [Dokploy](https://dokploy.com)، Coolify، Portainer یا هر VPS اجرا می‌شه.
* **قابل توسعه** — کدبیس کوچک و تست‌شده با پایتون (python-telegram-bot + SQLite) و بدون فریم‌ورک سنگین.

### راه‌اندازی سریع

۱. از [@BotFather](https://t.me/BotFather) یک بات بساز و توکن رو بردار. (پیشنهاد: `/setjoingroups` ← Disable)

۲. یک **کانال خالی برای پلی‌لیست** بساز و بات رو ادمین **هر دو کانال** کن:
   * کانال اصلی: ادمین، بدون دسترسی اضافه
   * کانال پلی‌لیست: ادمین با **Post messages** و **Delete messages**

۳. آی‌دی عددی خودت ([@userinfobot](https://t.me/userinfobot)) و آی‌دی دو کانال (`-100…` مثلاً با [@RawDataBot](https://t.me/RawDataBot)) رو پیدا کن.

۴. تنظیم و اجرا:

```bash
git clone https://github.com/alirezajokar/tg_playlist_bot.git
cd tg_playlist_bot
cp .env.example .env      # BOT_TOKEN, OWNER_IDS, SOURCE_CHANNEL_ID, PLAYLIST_CHANNEL_ID رو پر کن
docker compose --env-file .env up -d --build
```

روی **Dokploy**: یک پروژه‌ی *Docker Compose* از همین ریپو بساز و چهار متغیر بالا رو تو تب Environment بذار. دیتابیس توی volume به اسم `bot_data` می‌مونه و با redeploy پاک نمی‌شه.

۵. تو چت خصوصی با بات `/status` بفرست؛ دسترسی بات به هر دو کانال رو چک می‌کنه.

### ایمپورت موزیک‌های قدیمی

تلگرام دسکتاپ ← کانال ← ⋮ ← **Export chat history** ← تیک همه‌ی Media رو بردار ← **Format: JSON** (نه HTML!) ← Export. بعد:

* فایل `result.json` رو تو چت خصوصی برای بات بفرست (حداکثر ۲۰ مگابایت؛ برای هزاران موزیک بدون مدیا کافیه)، یا
* `docker cp result.json <container>:/tmp/result.json && docker exec <container> python -m app.import_cli /tmp/result.json`

فقط پست‌های موزیک وارد می‌شن (متن، عکس، ویدیو و ویس نادیده گرفته می‌شن). ایمپورت تکرارپذیره، داده‌ی جدیدتر رو overwrite نمی‌کنه و اکسپورت کانال اشتباه رو رد می‌کنه.

### نحوه‌ی جست‌وجو

هر متنی که تو چت خصوصی بفرستی یک جست‌وجوئه:

| ورودی | معنی |
|---|---|
| `ebi` | اول‌کلمه‌ی `ebi` تو خواننده / آهنگ / اسم فایل / کپشن / هشتگ (`Rebirth` رو **نمی‌گیره**) |
| `#remix` | هشتگ دقیق `#remix` |
| `#remix #rap` | هر دو هشتگ |
| `ebi -#remix` | ebi ولی بدون ریمیکس |
| `artist:ebi` · `title:shab` | فقط تو خواننده / فقط تو اسم آهنگ |
| `"shab bokhor"` | عبارت دقیق |

دستورها: `/tags` `/artists` `/stats` `/status` `/clear` `/stop` `/import` `/help`

### تنظیمات

| متغیر | اجباری | پیش‌فرض | توضیح |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | | توکن از @BotFather |
| `OWNER_IDS` | ✅ | | آی‌دی عددی کاربرهای مجاز، با کاما جدا شده |
| `SOURCE_CHANNEL_ID` | ✅ | | کانال موزیک‌ها (`-100…`) |
| `PLAYLIST_CHANNEL_ID` | ✅ | | کانال خالی پلی‌لیست (باید با کانال اصلی فرق داشته باشه) |
| `DB_PATH` | | `/data/playlist.db` | فایل SQLite |
| `SEND_DELAY` | | `1.0` | فاصله‌ی ثانیه‌ای بین ارسال دو آهنگ |
| `MAX_PLAYLIST_SIZE` | | `500` | سقف تعداد آهنگ در هر پلی‌لیست |
| `LOG_LEVEL` | | `INFO` | سطح لاگ |

### امنیت

* **فقط مالک:** پیام و دکمه‌ی کسی که تو `OWNER_IDS` نیست نادیده گرفته می‌شه.
* فقط پست‌های `SOURCE_CHANNEL_ID` ایندکس می‌شن؛ اگه کانال اصلی و پلی‌لیست یکی باشن، بات بالا نمیاد.
* بات فقط پیام‌هایی رو پاک می‌کنه که خودش ثبت کرده؛ هیچ‌وقت چیزی از کانال اصلی پاک نمی‌شه.
* توکن هیچ‌جا چاپ نمی‌شه (لاگ URL ها خاموشه و همه‌ی لاگ‌ها redact می‌شن).
* همه‌ی SQLها پارامتری‌اند؛ متن‌ها قبل از نمایش HTML-escape می‌شن؛ ایمپورت فقط JSON با محدودیت حجم است.
* کانتینر با کاربر غیر root، فایل‌سیستم فقط‌خواندنی، بدون capability و بدون پورت اجرا می‌شه.
* مشکل امنیتی پیدا کردی؟ [SECURITY.md](SECURITY.md) رو ببین.

### سؤال‌های پرتکرار

**بات خودش پیام‌های قدیمی کانال رو می‌خونه؟** نه؛ Bot API تلگرام اجازه‌ی خوندن تاریخچه‌ی کانال رو نمی‌ده. برای همین یک بار ایمپورت JSON لازمه؛ بعدش همه‌چیز خودکاره.

**چرا کپی، نه فوروارد؟** کپی برچسب «forwarded from» نداره و آهنگ، کپشن و هشتگ‌ها رو دست‌نخورده نگه می‌داره.

**اگه آهنگی رو از کانال پاک کنم بات می‌فهمه؟** تلگرام حذف رو به بات خبر نمی‌ده؛ بات وقتی می‌خواد آهنگ ناموجود رو کپی کنه می‌فهمه و از دیتابیس حذفش می‌کنه.

**چند نفر می‌تونن از یک بات استفاده کنن؟** فعلاً نه؛ عمداً ابزار تک‌مالکه (یک کتابخونه، یک کانال پلی‌لیست). هر کس تو چند دقیقه نمونه‌ی خودش رو بالا میاره.

**عمومی کردن کانال پلی‌لیست قانونیه؟** بات فقط پست‌های کانال خودت رو کپی می‌کنه، ولی پخش عمومی موزیک دارای کپی‌رایت مسئولیت خودته.

### ایده‌های آینده (مشارکت خوش‌آمده)

مرتب‌سازی تصادفی/جدیدترین‌اول · alias برای خواننده‌ها (`ebi` ⇄ `ابی`) · ایمپورت از اکسپورت HTML · دستور `/random N` · زبان‌های بیشتر · چند کانال پلی‌لیست.

### مشارکت

Issue و Pull Request خیلی خوش‌آمده — [CONTRIBUTING.md](CONTRIBUTING.md) رو ببین.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

### لایسنس

[MIT](LICENSE)

</div>
