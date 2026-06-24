from types import SimpleNamespace

import pytest
from feeluown.excs import ProviderIOError

from fuo_ytmusic.provider import YtmusicProvider


def test_song_get_handles_watch_playlist_thumbnail_and_length_fields():
    song_id = "vid-1"
    expected_pic_url = "https://example.com/song-544.jpg"

    class _ApiStub:
        @staticmethod
        def get_watch_playlist(identifier):
            assert identifier == song_id
            return {
                "tracks": [
                    {
                        "videoId": song_id,
                        "title": "Song A",
                        "artists": [{"id": "artist-1", "name": "Artist A"}],
                        "album": {"id": "album-1", "name": "Album A"},
                        "length": "3:00",
                        "thumbnail": [
                            {
                                "url": "https://example.com/song-60.jpg",
                                "width": 60,
                                "height": 60,
                            },
                            {
                                "url": expected_pic_url,
                                "width": 544,
                                "height": 544,
                            },
                        ],
                        "feedbackTokens": {},
                        "isAvailable": True,
                        "isExplicit": False,
                    }
                ]
            }

    class _ServiceStub:
        api = _ApiStub()

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    song = provider.song_get(song_id)

    assert song.identifier == song_id
    assert song.pic_url == expected_pic_url
    assert song.duration > 0


def test_song_list_similar_handles_watch_playlist_thumbnail_and_length_fields():
    seed_song_id = "seed-song"

    class _ApiStub:
        @staticmethod
        def get_watch_playlist(identifier):
            assert identifier == seed_song_id
            return {
                "tracks": [
                    {"videoId": seed_song_id, "title": "Seed Song"},
                    {
                        "videoId": "sim-1",
                        "title": "Similar Song",
                        "artists": [{"id": "artist-1", "name": "Artist A"}],
                        "album": {"id": "album-1", "name": "Album A"},
                        "length": "4:20",
                        "thumbnail": [
                            {
                                "url": "https://example.com/sim-544.jpg",
                                "width": 544,
                                "height": 544,
                            }
                        ],
                        "feedbackTokens": {},
                        "isAvailable": True,
                        "isExplicit": False,
                    },
                ]
            }

    class _ServiceStub:
        api = _ApiStub()

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    songs = provider.song_list_similar(SimpleNamespace(identifier=seed_song_id))

    assert len(songs) == 1
    assert songs[0].identifier == "sim-1"
    assert songs[0].pic_url == "https://example.com/sim-544.jpg"
    assert songs[0].duration > 0


def test_song_get_lyric_returns_lyric_model():
    class _ServiceStub:
        @staticmethod
        def song_lyrics(identifier):
            assert identifier == "video-id"
            return "line 1\nline 2"

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    lyric = provider.song_get_lyric(SimpleNamespace(identifier="video-id"))

    assert lyric.identifier == "video-id"
    assert lyric.source == provider.identifier
    assert lyric.content == "line 1\nline 2"
    assert lyric.trans_content == ""


def test_song_get_lyric_returns_none_when_unavailable():
    class _ServiceStub:
        @staticmethod
        def song_lyrics(identifier):
            assert identifier == "video-id"
            return None

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    assert provider.song_get_lyric(SimpleNamespace(identifier="video-id")) is None


def test_song_get_lyric_wraps_service_error():
    class _ServiceStub:
        @staticmethod
        def song_lyrics(_identifier):
            raise RuntimeError("network failed")

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    with pytest.raises(ProviderIOError, match="get song lyric failed"):
        provider.song_get_lyric(SimpleNamespace(identifier="video-id"))
