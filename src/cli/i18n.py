import gettext
import os
from functools import lru_cache
from pathlib import Path

DOMAIN = "msgram"
LOCALE_DIR = Path(__file__).resolve().parent / "locale"


def _env(var: str) -> str:
    return os.environ.get(var, "").strip()


def _is_c_locale(value: str) -> bool:
    return value.split(".")[0].split("@")[0].upper() in ("C", "POSIX")


def _with_fallback(languages: list[str]) -> tuple[str, ...]:
    return (*(lang.replace("-", "_") for lang in languages if lang), "en")


def _get_languages() -> tuple[str, ...]:
    override = _env("MSGRAM_LANG")
    if override:
        return ("en",) if _is_c_locale(override) else _with_fallback([override])
    locale = next(
        (_env(var) for var in ("LC_ALL", "LC_MESSAGES", "LANG") if _env(var)), ""
    )
    if not locale or _is_c_locale(locale):
        return ("en",)
    language_list = _env("LANGUAGE")
    if language_list:
        return _with_fallback(language_list.split(":"))
    return _with_fallback([locale])


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
