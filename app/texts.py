"""All user-facing strings (Persian) in one place."""

HELP = """🎵 <b>ربات پلی‌لیست</b>

یک عبارت بفرست تا بین موزیک‌های کانالت بگردم. بعد با یک دکمه همه‌ی نتایج داخل کانال پلی‌لیست ریخته می‌شه (و پلی‌لیست قبلی اول پاک می‌شه).

<b>نمونه‌ی جست‌وجو</b>
<code>ebi</code> ← هر موزیکی که ebi تو اسم خواننده، اسم آهنگ، کپشن یا هشتگش باشه
<code>#remix</code> ← هشتگ دقیق remix
<code>#remix #rap</code> ← هر دو هشتگ
<code>ebi -#remix</code> ← ebi ولی بدون ریمیکس
<code>artist:ebi</code> ← فقط تو اسم خواننده
<code>title:shab</code> ← فقط تو اسم آهنگ
<code>"shab bokhor"</code> ← عبارت دقیق

<b>دستورها</b>
/tags ← هشتگ‌ها و تعدادشون
/artists ← خواننده‌ها و تعدادشون
/stats ← آمار کتابخونه
/status ← بررسی دسترسی بات به کانال‌ها
/clear ← خالی کردن کانال پلی‌لیست
/stop ← توقف ساخت پلی‌لیست در حال انجام
/import ← راهنمای ایمپورت موزیک‌های قدیمی

موزیک‌های جدید و ویرایش‌ها (کپشن/هشتگ) خودکار از کانال اصلی خونده می‌شن."""

IMPORT_HELP = """📥 <b>ایمپورت موزیک‌های قدیمی</b>

بات‌ها نمی‌تونن تاریخچه‌ی کانال رو بخونن، پس یک بار اکسپورت می‌گیریم:
۱. تلگرام دسکتاپ ← کانال موزیک ← منوی ⋮ ← Export chat history
۲. همه‌ی تیک‌های Media رو بردار، Format = <b>JSON</b>
۳. فایل <code>result.json</code> رو همین‌جا برای من بفرست.

اگه فایل بزرگ‌تر از ۲۰ مگابایت بود، روی سرور بذارش و اجرا کن:
<code>docker cp result.json &lt;container&gt;:/tmp/result.json
docker exec &lt;container&gt; python -m app.import_cli /tmp/result.json</code>

بعد از ایمپورت، بات برای موزیک‌های جدید خودش آپدیت می‌شه."""

NOT_FOUND = "چیزی پیدا نشد 🤷"
EMPTY_QUERY = "یک عبارت برای جست‌وجو بفرست. /help"
EXPIRED = "این پیش‌نمایش منقضی شده؛ دوباره جست‌وجو کن."
BUSY = "یک پلی‌لیست در حال ساخته شدنه. صبر کن یا /stop بزن."
NOTHING_RUNNING = "چیزی در حال اجرا نیست."
STOPPING = "⏹ در حال توقف…"
TOO_MANY = "نتیجه {n} موزیکه و سقف پلی‌لیست {max} تاست. جست‌وجو رو دقیق‌تر کن."
IMPORT_TOO_BIG = "فایل بزرگ‌تر از ۲۰ مگابایته؛ از روش docker exec (/import) استفاده کن."
IMPORT_NOT_JSON = "برای ایمپورت یک فایل <code>.json</code> بفرست. /import"
