import fuo_ytmusic.language as lang


class DummyApp:
    def __init__(self, language_code=None):
        if language_code is not None:
            self.language_code = language_code


def test_coerce_language_supported_exact():
    assert lang.coerce_language("en") == "en"
    assert lang.coerce_language("zh_CN") == "zh_CN"
    assert lang.coerce_language("zh-TW") == "zh_TW"


def test_coerce_language_chinese_regions():
    assert lang.coerce_language("zh_HK") == "zh_TW"
    assert lang.coerce_language("zh-MO") == "zh_TW"
    assert lang.coerce_language("zh_SG") == "zh_CN"


def test_coerce_language_primary_fallback():
    assert lang.coerce_language("en_US") == "en"
    assert lang.coerce_language("pt_BR") == "pt"


def test_coerce_language_unknown():
    assert lang.coerce_language("xx_YY") == "zh_CN"


def test_resolve_language_config_override():
    app = DummyApp(language_code="en_US")
    assert lang.resolve_language(app, "ja") == "ja"


def test_resolve_language_app_language():
    app = DummyApp(language_code="en_US")
    assert lang.resolve_language(app, "auto") == "en"


def test_resolve_language_locale_fallback(monkeypatch):
    app = DummyApp()

    monkeypatch.setattr(
        lang.locale, "getlocale", lambda category=None: ("pt_BR", "UTF-8")
    )
    assert lang.resolve_language(app, "auto") == "pt"

    monkeypatch.setattr(lang.locale, "getlocale", lambda category=None: (None, None))
    assert lang.resolve_language(app, "auto") == "zh_CN"
