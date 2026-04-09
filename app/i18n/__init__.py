from __future__ import annotations

import json
from functools import lru_cache

from app.config import Locale, get_settings


SUPPORTED_LOCALES: set[Locale] = {"ru", "uz_cyrl", "uz_latn"}


def normalize_locale(value: str | None) -> Locale:
    if value in SUPPORTED_LOCALES:
        return value
    if value == "uz":
        return "uz_latn"
    return get_settings().default_locale


@lru_cache(maxsize=1)
def _load_translations() -> dict[str, dict[str, str]]:
    settings = get_settings()
    translations: dict[str, dict[str, str]] = {}
    for locale in SUPPORTED_LOCALES:
        path = settings.i18n_dir / f"{locale}.json"
        translations[locale] = json.loads(path.read_text(encoding="utf-8"))
    return translations


def t(locale: str | None, key: str, **kwargs: object) -> str:
    resolved = normalize_locale(locale)
    text = _load_translations()[resolved].get(key) or _load_translations()["ru"].get(key) or key
    return text.format(**kwargs)
