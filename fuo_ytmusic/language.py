from typing import Optional
import locale

from ytmusicapi.constants import SUPPORTED_LANGUAGES


def resolve_language(app, configured: Optional[str] = None) -> str:
    # LANGUAGE config has highest priority; support "auto" for legacy behavior.
    if configured and str(configured).lower() != "auto":
        return coerce_language(str(configured))

    # New FeelUOwn provides app.language_code; older versions do not.
    language = getattr(app, "language_code", None)
    if not language:
        # Fallback to system locale (may be None or "C" on some platforms).
        language, _ = locale.getlocale(locale.LC_CTYPE)
    if not language:
        # Conservative default for this plugin.
        return "zh_CN"
    return coerce_language(language)


def coerce_language(language: str) -> str:
    # Normalize and map to ytmusicapi supported languages.
    normalized = language.replace("-", "_")
    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    # Special-case Chinese: map regions to zh_CN / zh_TW.
    primary = normalized.split("_")[0].lower()
    if primary == "zh":
        parts = normalized.split("_")
        region = parts[1].upper() if len(parts) >= 2 else ""
        if region in {"TW", "HK", "MO"}:
            return "zh_TW"
        return "zh_CN"

    # Use primary language if supported (e.g., en_US -> en).
    if primary in SUPPORTED_LANGUAGES:
        return primary
    # Final fallback to a known supported language.
    return "zh_CN"
