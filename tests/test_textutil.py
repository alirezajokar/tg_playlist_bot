from app.textutil import extract_hashtags, norm, norm_tag


def test_norm_basics():
    assert norm("Ebi - Shab_Bokhor (Remix)!") == "ebi shab bokhor remix"
    assert norm("كيان ۱۲۳") == "کیان 123"
    assert norm("می‌خوام") == "می خوام"
    assert norm("Beyoncé") == "beyonce"
    assert norm("آهنگ") == "اهنگ"


def test_hashtags():
    assert extract_hashtags("hi #Remix #rap #remix #پاپ_ایرانی") == ["remix", "rap", "پاپ_ایرانی"]
    assert extract_hashtags("nothing") == []
    assert norm_tag("#پاپ‌ایرانی") == "پاپ_ایرانی"
