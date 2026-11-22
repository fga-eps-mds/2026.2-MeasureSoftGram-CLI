import pytest


@pytest.fixture(autouse=True)
def _default_english_locale(monkeypatch):
    """Keep CLI output in English during tests regardless of host locale."""
    monkeypatch.setenv("MSGRAM_LANG", "en")
