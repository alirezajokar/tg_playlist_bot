# Contributing / مشارکت

Thanks for helping! Bug reports, ideas, docs fixes, translations and pull requests are all welcome.
ممنون که کمک می‌کنی! گزارش باگ، ایده، اصلاح مستندات، ترجمه و PR همه خوش‌آمدند.

## Quick start / شروع سریع

```bash
git clone https://github.com/alirezajokar/tg_playlist_bot.git
cd tg_playlist_bot
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

No Telegram token is needed to run the tests: the Telegram API is faked (see `tests/test_playlist.py`).
برای اجرای تست‌ها توکن لازم نیست؛ API تلگرام در تست‌ها شبیه‌سازی شده.

## Where things live / ساختار

| File | Purpose |
|---|---|
| `app/search.py` | query language → parameterised SQL |
| `app/ingest.py` | channel posts and Telegram Desktop export → `Track` |
| `app/db.py` | SQLite schema, migrations (`_MIGRATIONS`), queries |
| `app/playlist.py` | wipe + refill the playlist channel (flood-wait, cancel) |
| `app/bot.py` | Telegram handlers (UI) |
| `app/texts.py` | all user-facing (Persian) strings |

## Guidelines / قواعد

* Keep it simple — prefer a small, readable change over an abstraction.
* Add or update tests for behaviour changes; `python -m pytest` must pass.
* **Security first:** never build SQL with string formatting of user input, escape anything shown with
  `parse_mode=HTML`, never log the token, and keep the bot owner-only.
* One topic per pull request; describe *why*, not only *what*.
* Good first issues: more languages for `app/texts.py`, a parser for the HTML export, shuffle /
  newest-first ordering, artist aliases (e.g. `ebi` = `ابی`), a `/random N` command.

## Reporting bugs / گزارش باگ

Include: what you did, what you expected, what happened, and the relevant log lines
(the token is redacted automatically — still double-check before pasting).
Security problems: see [SECURITY.md](SECURITY.md).
