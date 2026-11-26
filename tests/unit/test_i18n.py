import pytest

from src.cli import i18n
from src.cli.parsers import create_parser


def _clear_lang_env(monkeypatch):
    for var in ("MSGRAM_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)


def test_fallback_to_english_when_no_language_set(monkeypatch):
    _clear_lang_env(monkeypatch)
    assert i18n._("Extract supported metrics") == "Extract supported metrics"


def test_fallback_to_english_for_unsupported_or_c_locale(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LANG", "C.UTF-8")
    assert i18n._("Extract supported metrics") == "Extract supported metrics"

    monkeypatch.setenv("MSGRAM_LANG", "fr_FR")
    assert i18n._("Extract supported metrics") == "Extract supported metrics"


@pytest.mark.parametrize("c_locale", ["C", "C.UTF-8", "C.utf8", "POSIX"])
def test_lc_all_c_wins_over_lang(monkeypatch, c_locale):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    monkeypatch.setenv("LC_ALL", c_locale)
    assert i18n._("Extract supported metrics") == "Extract supported metrics"


def test_language_variable_comes_before_locale(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("LANGUAGE", "pt_BR:en")
    assert i18n._("Extract supported metrics") == "Extrai métricas suportadas"


def test_language_variable_is_ignored_with_c_locale(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LANG", "C.UTF-8")
    monkeypatch.setenv("LANGUAGE", "pt_BR")
    assert i18n._("Extract supported metrics") == "Extract supported metrics"


def test_lang_pt_br_translates(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    assert i18n._("Extract supported metrics") == "Extrai métricas suportadas"


def test_translates_with_msgram_lang_pt_br(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("MSGRAM_LANG", "pt_BR")
    assert i18n._("Extract supported metrics") == "Extrai métricas suportadas"


def test_msgram_lang_overrides_system_locale(monkeypatch):
    _clear_lang_env(monkeypatch)
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.setenv("MSGRAM_LANG", "pt-BR")
    assert i18n._("Calculates all entities") == "Calcula todas as entidades"


def test_argparse_help_respects_language(monkeypatch):
    _clear_lang_env(monkeypatch)
    assert "Command line interface for measuresoftgram" in create_parser().format_help()

    monkeypatch.setenv("MSGRAM_LANG", "pt_BR")
    assert (
        "Interface de linha de comando para o MeasureSoftGram"
        in create_parser().format_help()
    )


def test_weights_messages_follow_language(monkeypatch):
    from src.cli.commands.cmd_weights import describe_answer, format_cr

    _clear_lang_env(monkeypatch)
    answer = ("a", "b", "a", "fortemente")
    assert format_cr(0.0495) == "0.05"
    assert describe_answer(answer) == "a × b: a is strongly more important"

    monkeypatch.setenv("MSGRAM_LANG", "pt_BR")
    assert format_cr(0.0495) == "0,05"
    assert describe_answer(answer) == "a × b: a é fortemente mais importante"


def test_weights_plural_follows_language(monkeypatch):
    _clear_lang_env(monkeypatch)
    singular, plural = (
        "[{title}] {label} ({n} comparison)",
        "[{title}] {label} ({n} comparisons)",
    )
    assert i18n.ngettext(singular, plural, 2).endswith("comparisons)")

    monkeypatch.setenv("MSGRAM_LANG", "pt_BR")
    assert i18n.ngettext(singular, plural, 1).endswith("comparação)")
    assert i18n.ngettext(singular, plural, 3).endswith("comparações)")
