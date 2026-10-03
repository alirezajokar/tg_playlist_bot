# Security Policy / سیاست امنیتی

## Reporting a vulnerability / گزارش آسیب‌پذیری

Please **do not open a public issue** for security problems.
Use GitHub's private reporting: **Security → Report a vulnerability** on this repository.
We will acknowledge within a few days and fix confirmed issues as soon as possible.

لطفاً مشکل امنیتی را در Issue عمومی ننویس؛ از بخش **Security → Report a vulnerability** همین ریپو استفاده کن.

## Scope / دامنه

This bot is **single-tenant by design**: only the user ids listed in `OWNER_IDS` can control it,
and it only indexes posts from `SOURCE_CHANNEL_ID`. Reports about bypassing that, leaking the bot
token (logs, errors), SQL/HTML injection, or the bot deleting messages it did not post are in scope.

## Hardening checklist for self-hosters / چک‌لیست میزبان‌ها

* Keep `BOT_TOKEN` only in environment variables / your deployment secrets. Never commit `.env`.
  If it leaks, revoke it with `/revoke` in @BotFather.
* Disable "Allow Groups" for the bot in @BotFather (`/setjoingroups`).
* Give the bot the minimum channel rights (README → Setup).
* Keep the Docker image and dependencies up to date.
