import pytest

from app.db import Database
from app.models import Track


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    yield d
    d.close()


@pytest.fixture
def library(db):
    db.upsert_many([
        Track(1, title="Shab Bokhor", performer="Ebi", caption="#pop #classic"),
        Track(2, title="Rebirth", performer="Someone", caption="#remix"),
        Track(3, title="Ghesse", performer="Mohsen Yeganeh", file_name="ebi - ghesse.mp3", caption="#Remix #rap"),
        Track(4, title="سلام", performer="ابی", caption="#پاپ_ایرانی #ریمیکس"),
        Track(5, title="Other", performer="X", caption="no tags"),
    ], origin="import")
    return db
