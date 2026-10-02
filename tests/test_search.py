from app.search import Clause, parse_query


def ids(db, q):
    return [t.message_id for t in db.find(parse_query(q))]


def test_parse():
    assert parse_query('ebi -#remix artist:Ebi "shab bokhor" foo:bar') == [
        Clause("all", "ebi"), Clause("tag", "remix", True), Clause("artist", "ebi"),
        Clause("all", "shab bokhor"), Clause("all", "foo bar"),
    ]
    assert parse_query("  - ") == []


def test_word_prefix_not_substring(library):
    # "ebi" must find Ebi (artist) and the file name, but not "Rebirth"
    assert ids(library, "ebi") == [1, 3]


def test_fields(library):
    assert ids(library, "artist:ebi") == [1]
    assert ids(library, "title:ghesse") == [3]
    assert ids(library, "title:ebi") == []


def test_tags(library):
    assert ids(library, "#remix") == [2, 3]
    assert ids(library, "#remix #rap") == [3]
    assert ids(library, "#remix -#rap") == [2]
    assert ids(library, "ebi -#remix") == [1]
    assert ids(library, "#rem") == []  # exact hashtag only


def test_persian(library):
    assert ids(library, "ابی") == [4]
    assert ids(library, "#ریمیکس") == [4]
    assert ids(library, "#پاپ_ایرانی") == [4]


def test_phrase_and_and(library):
    assert ids(library, '"shab bokhor"') == [1]
    assert ids(library, "shab pop") == [1]
    assert ids(library, "shab rap") == []


def test_sql_injection_and_wildcards(library):
    assert ids(library, "' OR 1=1 --") == []
    assert parse_query("% _") == []  # pure punctuation normalises away; the bot rejects empty queries
    assert ids(library, "e%i") == []
    assert ids(library, "e_i") == []
    assert ids(library, '"; DROP TABLE tracks; --') == []
    assert library.stats()["tracks"] == 5


def test_deleted_hidden(library):
    library.mark_deleted(1)
    assert ids(library, "ebi") == [3]
