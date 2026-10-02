from app.bot import PlaylistBot, Pending
from app.models import Track
from app.playlist import PublishResult
from tests.test_routing import CFG


def test_render_escapes_html_and_pages(db):
    bot = PlaylistBot(CFG, db)
    tracks = [Track(i, title=f"<b>x{i}</b> & co", performer="A", tags=("remix",)) for i in range(1, 40)]
    bot.pending["abc"] = Pending("<script>", tracks)
    body, markup = bot.render("abc", 1)
    assert "<script>" not in body and "&lt;script&gt;" in body
    assert "<b>x" not in body.replace("<b>&lt;", "")  # only our own <b> header tag survives
    assert "16." in body and "30." in body and "31." not in body
    assert all(len(b.callback_data) <= 64 for row in markup.inline_keyboard for b in row)
    assert markup.inline_keyboard[0][1].text == "2/3"


def test_summary_reports_problems():
    text = PlaylistBot.summary("q<", PublishResult(sent=3, missing=1, failed=2, clear_failed=1, error="boom"))
    assert "q&lt;" in text and "boom" in text and "3" in text
