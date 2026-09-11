from api.domain.article.models import Lang
from worker.technical.lang_detect import detect_lang

FRENCH_TEXT = "Le chat est dans le jardin avec la souris et il mangeait des croquettes."
ENGLISH_TEXT = "The cat is in the garden with the mouse and it was eating some biscuits."
GERMAN_TEXT = "Die Katze sitzt im Garten mit der Maus und frisst gerne Kekse am Nachmittag."
SPANISH_TEXT = "El gato esta en el jardin con el raton y estaba comiendo unas galletas."
ITALIAN_TEXT = "Il gatto e nel giardino con il topo e stava mangiando dei biscotti."
PORTUGUESE_TEXT = "O gato esta no jardim com o rato e estava comendo alguns biscoitos."
RUSSIAN_TEXT = "Кошка сидит в саду с мышью и ела печенье во второй половине дня."
ARABIC_TEXT = "القطة في الحديقة مع الفأر وكانت تأكل بعض البسكويت بعد الظهر."
CHINESE_TEXT = "这只猫在花园里和老鼠一起玩耍，它下午喜欢吃饼干。"
MALAGASY_TEXT = "Ilay saka dia ao amin ny zaridaina miaraka amin ny voalavo ary nihinana mofomamy."


def test_detect_lang_identifies_french() -> None:
    assert detect_lang(FRENCH_TEXT) == Lang.FR


def test_detect_lang_identifies_english() -> None:
    assert detect_lang(ENGLISH_TEXT) == Lang.EN


def test_detect_lang_identifies_german() -> None:
    assert detect_lang(GERMAN_TEXT) == Lang.DE


def test_detect_lang_identifies_spanish() -> None:
    assert detect_lang(SPANISH_TEXT) == Lang.ES


def test_detect_lang_identifies_italian() -> None:
    assert detect_lang(ITALIAN_TEXT) == Lang.IT


def test_detect_lang_identifies_portuguese() -> None:
    assert detect_lang(PORTUGUESE_TEXT) == Lang.PT


def test_detect_lang_identifies_russian() -> None:
    assert detect_lang(RUSSIAN_TEXT) == Lang.RU


def test_detect_lang_identifies_arabic() -> None:
    assert detect_lang(ARABIC_TEXT) == Lang.AR


def test_detect_lang_identifies_chinese() -> None:
    assert detect_lang(CHINESE_TEXT) == Lang.ZH


def test_detect_lang_falls_back_to_malagasy_when_unrecognized() -> None:
    """No detector profile covers Malagasy: an unrecognized text lands on the one language with
    no stemmer either, rather than being guessed into a random covered language."""
    assert detect_lang(MALAGASY_TEXT) == Lang.MG


def test_detect_lang_falls_back_to_malagasy_on_empty_text() -> None:
    assert detect_lang("") == Lang.MG
