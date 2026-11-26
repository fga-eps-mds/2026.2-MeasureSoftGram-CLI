import pytest

from src.cli import i18n


@pytest.fixture(scope="session", autouse=True)
def _compiled_catalog():
    po_path = i18n.LOCALE_DIR / "pt_BR" / "LC_MESSAGES" / f"{i18n.DOMAIN}.po"
    mo_path = po_path.with_suffix(".mo")
    if not mo_path.exists() or po_path.stat().st_mtime > mo_path.stat().st_mtime:
        from babel.messages import mofile, pofile

        with po_path.open("rb") as po_file:
            catalog = pofile.read_po(po_file, locale="pt_BR")
        with mo_path.open("wb") as mo_file:
            mofile.write_mo(mo_file, catalog)
    i18n._load_translation.cache_clear()


@pytest.fixture(autouse=True)
def _default_english_locale(monkeypatch):
    """Keep CLI output in English during tests regardless of host locale."""
    monkeypatch.setenv("MSGRAM_LANG", "en")
