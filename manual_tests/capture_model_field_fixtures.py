"""Capture real YTMusic payloads and export raw test fixtures.

Usage:
  YTMUSIC_MANUAL_PROXY=http://127.0.0.1:7890 \
    uv run python manual_tests/capture_model_field_fixtures.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.service import YtmusicService

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Use stable objects so fixtures can be refreshed predictably.
SINGLE_ALBUM_ID = "MPREb_lUTbpM4Z2C7"  # Adele - Hello (single)
EP_ALBUM_ID = "MPREb_Ag93Bmsdecj"  # Shape of You (EP)
ARTIST_ID = "UCRw0x9_EfawqmgDI2IgQLLg"  # Adele


def _write_fixture(filename: str, payload: dict):
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURES_DIR / filename
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote fixture: {path}")


def main():
    if not HEADER_FILE.exists():
        raise SystemExit(f"header file not found: {HEADER_FILE}")

    service = YtmusicService()
    proxy = os.getenv("YTMUSIC_MANUAL_PROXY", "").strip()
    if proxy:
        service.setup_http_proxy(proxy)
    service.setup_timeout(12)
    service.setup_language("en")
    service.reinitialize_by_headerfile(HEADER_FILE)

    album = service.api.get_album(SINGLE_ALBUM_ID)
    album_ep = service.api.get_album(EP_ALBUM_ID)
    artist = service.api.get_artist(ARTIST_ID)
    tracks = album.get("tracks") or []
    if not tracks:
        raise SystemExit("album payload has no tracks; cannot build song fixture")
    song_id = tracks[0].get("videoId")
    if not song_id:
        raise SystemExit("album first track has no videoId; cannot build song fixture")
    song = service.api.get_song(song_id)

    videos = (artist.get("videos") or {}).get("results") or []
    if not videos:
        raise SystemExit("artist payload has no videos; cannot build video fixture")

    _write_fixture("model_fields_get_album_single.json", album)
    _write_fixture("model_fields_get_album_ep.json", album_ep)
    _write_fixture("model_fields_get_artist.json", artist)
    _write_fixture("model_fields_artist_video_item.json", videos[0])
    _write_fixture("model_fields_get_song.json", song)

    # Capture one zh-CN video entry to keep count parser tests grounded.
    service.setup_language("zh_CN")
    service.reinitialize_by_headerfile(HEADER_FILE)
    artist_zh = service.api.get_artist(ARTIST_ID)
    videos_zh = (artist_zh.get("videos") or {}).get("results") or []
    if videos_zh:
        _write_fixture("model_fields_artist_video_item_zh.json", videos_zh[0])


if __name__ == "__main__":
    main()
