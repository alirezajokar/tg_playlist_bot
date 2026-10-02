from app.models import Track


def test_upsert_status_and_tag_update(db):
    t = Track(10, title="A", performer="B", caption="#one")
    assert db.upsert_track(t) == "inserted"
    assert db.upsert_track(t) == "unchanged"
    t2 = Track(10, title="A", performer="B", caption="#one #two")
    assert db.upsert_track(t2) == "updated"
    assert dict(db.tag_counts()) == {"one": 1, "two": 1}
    t3 = Track(10, title="A", performer="B", caption="#two")  # hashtag removed -> bot notices
    assert db.upsert_track(t3) == "updated"
    assert dict(db.tag_counts()) == {"two": 1}


def test_import_does_not_override_live(db):
    db.upsert_track(Track(1, title="new", caption="#live"), origin="live")
    stats = db.upsert_many([Track(1, title="old", caption="#old"), Track(2, title="x")], origin="import")
    assert stats == {"inserted": 1, "updated": 0, "unchanged": 0, "skipped": 1}
    assert db.find([])[0].title == "new"


def test_edit_revives_deleted(db):
    db.upsert_track(Track(1, title="a"))
    db.mark_deleted(1)
    assert db.stats()["tracks"] == 0
    assert db.upsert_track(Track(1, title="a")) == "updated"
    assert db.stats()["tracks"] == 1


def test_artist_counts_and_persistence(tmp_path):
    from app.db import Database
    path = str(tmp_path / "p.db")
    d = Database(path)
    d.upsert_many([Track(1, performer="Ebi"), Track(2, performer="ebi"), Track(3, performer="Zed")])
    d.close()
    d = Database(path)  # reopening keeps data and schema
    assert d.artist_counts()[0][1] == 2
    d.close()
