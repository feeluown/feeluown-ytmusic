from types import SimpleNamespace

import pytest

from fuo_ytmusic.lyrics import (
    build_watch_playlist_body,
    extract_lyrics_browse_id,
    format_lrc_timestamp,
    timestamped_lyrics_to_lrc,
)


def test_build_watch_playlist_body():
    body = build_watch_playlist_body("video-id")

    assert body["videoId"] == "video-id"
    assert body["playlistId"] == "RDAMVMvideo-id"
    assert body["isAudioOnly"] is True


def test_extract_lyrics_browse_id_ignores_related_tab_without_endpoint():
    watch_response = _watch_response("MPLYt_lyrics", related_has_endpoint=False)

    assert extract_lyrics_browse_id(watch_response) == "MPLYt_lyrics"


def test_extract_lyrics_browse_id_returns_none_without_lyrics_endpoint():
    watch_response = _watch_response(None, related_has_endpoint=False)

    assert extract_lyrics_browse_id(watch_response) is None


def test_timestamped_lyrics_to_lrc_formats_ytmusic_lyric_lines():
    payload = {
        "lyrics": [
            SimpleNamespace(text="first line", start_time=9200),
            SimpleNamespace(text="second line", start_time=10680),
        ],
        "hasTimestamps": True,
    }

    assert (
        timestamped_lyrics_to_lrc(payload)
        == "[00:09.20]first line\n[00:10.68]second line"
    )


def test_timestamped_lyrics_to_lrc_returns_none_for_plain_text_payload():
    assert (
        timestamped_lyrics_to_lrc({"lyrics": "line 1\nline 2", "hasTimestamps": False})
        is None
    )


def test_timestamped_lyrics_to_lrc_raises_for_malformed_line():
    with pytest.raises(AttributeError):
        timestamped_lyrics_to_lrc({"lyrics": [{"text": "raw line", "start_time": 0}]})


def test_format_lrc_timestamp_rejects_non_int_start_time():
    with pytest.raises(TypeError):
        format_lrc_timestamp("1000")


def _watch_response(lyrics_browse_id, related_has_endpoint=True):
    lyrics_tab = {"tabRenderer": {"title": "Lyrics"}}
    if lyrics_browse_id:
        lyrics_tab["tabRenderer"]["endpoint"] = {
            "browseEndpoint": {"browseId": lyrics_browse_id}
        }

    related_tab = {"tabRenderer": {"title": "Related"}}
    if related_has_endpoint:
        related_tab["tabRenderer"]["endpoint"] = {
            "browseEndpoint": {"browseId": "MPLYt_related"}
        }

    return {
        "contents": {
            "singleColumnMusicWatchNextResultsRenderer": {
                "tabbedRenderer": {
                    "watchNextTabbedResultsRenderer": {
                        "tabs": [
                            {"tabRenderer": {"title": "Queue"}},
                            lyrics_tab,
                            related_tab,
                        ]
                    }
                }
            }
        }
    }
