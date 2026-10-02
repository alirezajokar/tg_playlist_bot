import pytest

from app.config import Config, ConfigError

GOOD = {"BOT_TOKEN": "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "OWNER_IDS": "1, 2",
        "SOURCE_CHANNEL_ID": "-1001", "PLAYLIST_CHANNEL_ID": "-1002"}


def test_ok_and_token_not_in_repr():
    cfg = Config.from_env(GOOD)
    assert cfg.owner_ids == {1, 2} and cfg.send_delay == 1.0
    assert "AAAA" not in repr(cfg)


@pytest.mark.parametrize("patch", [
    {"BOT_TOKEN": "bad"}, {"OWNER_IDS": ""}, {"OWNER_IDS": "abc"},
    {"PLAYLIST_CHANNEL_ID": "-1001"}, {"SEND_DELAY": "x"}, {"SOURCE_CHANNEL_ID": ""},
])
def test_invalid(patch):
    with pytest.raises(ConfigError):
        Config.from_env({**GOOD, **patch})
