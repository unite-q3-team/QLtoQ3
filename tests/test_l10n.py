import pytest

from qltoq3 import l10n


@pytest.fixture(autouse=True)
def restore_lang() -> None:
    prev = l10n.get_lang()
    try:
        yield
    finally:
        l10n.set_lang(prev)


def test_tr_formats_placeholders() -> None:
    l10n.set_lang("en")
    assert l10n.tr("stats.seconds", t=1.5) == "1.50 seconds"


def test_tr_falls_back_to_english_for_missing_key_in_current_lang() -> None:
    key = "tests.only_en"
    old_en = l10n.S["en"].get(key)
    old_ru = l10n.S["ru"].get(key)
    l10n.S["en"][key] = "value {n}"
    if key in l10n.S["ru"]:
        del l10n.S["ru"][key]
    try:
        l10n.set_lang("ru")
        assert l10n.tr(key, n=3) == "value 3"
    finally:
        if old_en is None:
            l10n.S["en"].pop(key, None)
        else:
            l10n.S["en"][key] = old_en
        if old_ru is None:
            l10n.S["ru"].pop(key, None)
        else:
            l10n.S["ru"][key] = old_ru


def test_tr_returns_key_when_missing_everywhere() -> None:
    l10n.set_lang("en")
    assert l10n.tr("tests.absent_key") == "tests.absent_key"


def test_default_lang_from_env_uses_explicit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QLTOQ3_LANG", "ru")
    monkeypatch.setattr(l10n, "_lang_from_prefs", lambda: None)
    assert l10n.default_lang_from_env() == "ru"
