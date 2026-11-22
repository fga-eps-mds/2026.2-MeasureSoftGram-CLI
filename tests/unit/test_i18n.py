import pytest
from babel.messages import mofile, pofile

from src.cli import i18n
from src.cli.parsers import create_parser


@pytest.fixture(scope="module", autouse=True)
def compiled_catalog():
    po_path = i18n.LOCALE_DIR / "pt_BR" / "LC_MESSAGES" / f"{i18n.DOMAIN}.po"
    mo_path = po_path.with_suffix(".mo")
    if not mo_path.exists() or po_path.stat().st_mtime > mo_path.stat().st_mtime:
        with po_path.open("rb") as po_file:
            catalog = pofile.read_po(po_file, locale="pt_BR")
        with mo_path.open("wb") as mo_file:
            mofile.write_mo(mo_file, catalog)
    i18n._load_translation.cache_clear()


def _clear_lang_env(monkeypatch):
    for var in ("MSGRAM_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
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
