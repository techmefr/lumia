from worker.technical.lang_detect import detect_lang


def test_detect_lang_identifies_french() -> None:
    assert detect_lang("Le chat est dans le jardin avec la souris") == "fr"


def test_detect_lang_identifies_english() -> None:
    assert detect_lang("The cat is in the garden with the mouse") == "en"
