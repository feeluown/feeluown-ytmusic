"""Manual stress test for yt-dlp media url resolution stability.

Run with:
  uv run pytest manual_tests/media_cookiefile_stress_test.py -s --run-manual-tests

Optional environment variables:
  YTMUSIC_MANUAL_PROXY      HTTP proxy url, e.g. http://127.0.0.1:7890
  YTMUSIC_MANUAL_TIMEOUT    socket timeout in seconds (default: 8)
  YTMUSIC_MANUAL_ATTEMPTS   attempts per mode (default: 3)
  YTMUSIC_MANUAL_SONG_IDS   comma-separated song ids (default: tn7rzN8ABuo,nBfUUj9kLLU)
"""

from __future__ import annotations

import os
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from feeluown.media import Quality

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.headerfile import (
    YtdlpCookiefileManager,
    read_headerfile,
)
from fuo_ytmusic.provider import provider


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_song_ids() -> list[str]:
    value = os.getenv("YTMUSIC_MANUAL_SONG_IDS", "").strip()
    if not value:
        return ["tn7rzN8ABuo", "nBfUUj9kLLU"]
    return [part.strip() for part in value.split(",") if part.strip()]


def _env_proxy() -> str:
    return (
        os.getenv("YTMUSIC_MANUAL_PROXY", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
    )


def _rebuild_cookiefile_from_header() -> Path | None:
    cookie = str(read_headerfile(HEADER_FILE).get("Cookie") or "")
    manager = YtdlpCookiefileManager(HEADER_FILE)
    return manager.write(cookie)


@contextmanager
def _temporarily_remove_cookiefile():
    manager = YtdlpCookiefileManager(HEADER_FILE)
    cookiefile = manager.cookiefile_path
    if cookiefile is None or not cookiefile.exists():
        yield
        return

    backup = cookiefile.with_suffix(cookiefile.suffix + ".bak")
    cookiefile.replace(backup)
    try:
        yield
    finally:
        if backup.exists():
            backup.replace(cookiefile)


def _run_attempts(song_id: str, attempts: int) -> tuple[Counter, Counter]:
    stats: Counter = Counter()
    reasons: Counter = Counter()
    for idx in range(1, attempts + 1):
        try:
            media = provider.song_get_media(
                SimpleNamespace(identifier=song_id),
                Quality.Audio.sq,
            )
            if media and media.url:
                stats["ok"] += 1
                print(f"  [{idx}] OK")
            else:
                stats["empty_url"] += 1
                print(f"  [{idx}] EMPTY_URL")
        except Exception as exc:  # manual diagnostics
            stats["fail"] += 1
            message = str(exc).splitlines()[0]
            reasons[message] += 1
            print(f"  [{idx}] FAIL {message}")
    return stats, reasons


@pytest.mark.manual
def test_cookiefile_stability_stress():
    if not HEADER_FILE.exists():
        print(f"headerfile not found: {HEADER_FILE}")
        return

    timeout = _env_int("YTMUSIC_MANUAL_TIMEOUT", 8)
    attempts = _env_int("YTMUSIC_MANUAL_ATTEMPTS", 3)
    proxy = _env_proxy()
    song_ids = _env_song_ids()
    if not song_ids:
        print("no song ids configured")
        return

    if proxy:
        provider.setup_http_proxy(proxy)
    provider.setup_http_timeout(timeout)

    user = provider.try_get_user_with_headerfile()
    if user is None:
        print("auto login failed, check ytmusic_header.json")
        return
    provider.auth(user)

    print(
        f"manual stress config: timeout={timeout}, attempts={attempts}, "
        f"proxy={'set' if proxy else 'unset'}"
    )

    for song_id in song_ids:
        print(f"\n=== song={song_id} with cookiefile ===")
        cookiefile = _rebuild_cookiefile_from_header()
        print(f"cookiefile rebuilt: {cookiefile}")
        with_stats, with_reasons = _run_attempts(song_id, attempts)
        print("with cookiefile summary:", dict(with_stats))
        for reason, count in with_reasons.items():
            print(f"  - x{count}: {reason}")

        print(f"\n=== song={song_id} without cookiefile ===")
        with _temporarily_remove_cookiefile():
            without_stats, without_reasons = _run_attempts(song_id, attempts)
        print("without cookiefile summary:", dict(without_stats))
        for reason, count in without_reasons.items():
            print(f"  - x{count}: {reason}")
