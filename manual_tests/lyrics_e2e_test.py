"""Manual end-to-end test for YTMusic timestamped lyrics.

Run with:
  uv run pytest manual_tests/lyrics_e2e_test.py -s --run-manual-tests

Optional environment variables:
  YTMUSIC_MANUAL_PROXY          HTTP proxy url, e.g. http://127.0.0.1:7890
  YTMUSIC_MANUAL_TIMEOUT        socket timeout in seconds (default: 8)
  YTMUSIC_MANUAL_LYRIC_SONG_IDS comma-separated song ids (default: tn7rzN8ABuo)
  YTMUSIC_MANUAL_USE_HEADERFILE set to 1 to authenticate with ytmusic_header.json
"""

from __future__ import annotations

import hashlib
import os
import socket
from types import SimpleNamespace

import pytest
from feeluown.player.lyric import parse_lyric_text

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.provider import provider


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_song_ids() -> list[str]:
    value = os.getenv("YTMUSIC_MANUAL_LYRIC_SONG_IDS", "").strip()
    if not value:
        return ["tn7rzN8ABuo"]
    return [part.strip() for part in value.split(",") if part.strip()]


def _env_proxy() -> str:
    return (
        os.getenv("YTMUSIC_MANUAL_PROXY", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
    )


def _setup_provider(timeout: int, proxy: str):
    socket.setdefaulttimeout(timeout)
    if proxy:
        provider.setup_http_proxy(proxy)
    provider.setup_http_timeout(timeout)

    if not _env_bool("YTMUSIC_MANUAL_USE_HEADERFILE"):
        print("running anonymously")
        return

    if not HEADER_FILE.exists():
        print(f"headerfile not found, running anonymously: {HEADER_FILE}")
        return

    user = provider.try_get_user_with_headerfile()
    if user is None:
        print("auto login failed, running anonymously")
        return
    provider.auth(user)


@pytest.mark.manual
def test_song_get_lyric_end_to_end():
    timeout = _env_int("YTMUSIC_MANUAL_TIMEOUT", 8)
    proxy = _env_proxy()
    song_ids = _env_song_ids()

    _setup_provider(timeout, proxy)
    print(
        f"manual lyrics config: timeout={timeout}, proxy={'set' if proxy else 'unset'}"
    )

    for song_id in song_ids:
        print(f"\n=== song={song_id} ===")
        lyric = provider.song_get_lyric(SimpleNamespace(identifier=song_id))
        if lyric is None:
            pytest.fail(f"no timestamped lyrics returned for {song_id}")

        parsed = parse_lyric_text(lyric.content)
        assert parsed, "lyric content should be parseable by FeelUOwn as LRC"
        print(f"timestamped lines: {len(parsed)}")
        summaries = []
        for line in lyric.content.splitlines()[:10]:
            timestamp = line.split("]", 1)[0] + "]" if "]" in line else ""
            digest = hashlib.sha1(line.encode()).hexdigest()[:10]
            summaries.append((timestamp, len(line), digest))
        print(f"first 10 line summaries: {summaries}")
        print(f"first 10 parsed timestamps: {list(parsed.keys())[:10]}")
