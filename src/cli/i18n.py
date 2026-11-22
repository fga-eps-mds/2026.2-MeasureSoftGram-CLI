import gettext
import os
from functools import lru_cache
from pathlib import Path

DOMAIN = "msgram"
LOCALE_DIR = Path(__file__).resolve().parent / "locale"


def _get_languages() -> tuple[str, ...]:
    for var in ("MSGRAM_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").strip()
        if value and value.upper() not in ("C", "C.UTF-8", "POSIX"):
            return (value.replace("-", "_"), "en")
    return ("en",)


@lru_cache(maxsize=8)
def _load_translation(languages: tuple[str, ...]) -> gettext.NullTranslations:
    return gettext.translation(
        DOMAIN,
        localedir=str(LOCALE_DIR),
        languages=list(languages),
        fallback=True,
    )


def _(message: str) -> str:
    """Translate a message using the active CLI language."""
    return _load_translation(_get_languages()).gettext(message)
