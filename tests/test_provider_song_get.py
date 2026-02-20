from types import SimpleNamespace

from fuo_ytmusic.provider import YtmusicProvider


def test_song_get_normalizes_watch_playlist_cover_and_duration():
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

        @staticmethod
        def song_info(_identifier):
            raise AssertionError("song_info fallback should not be used")

    provider = YtmusicProvider()
    provider.service = _ServiceStub()

    song = provider.song_get(song_id)

    assert song.identifier == song_id
    assert song.pic_url == expected_pic_url
    assert song.duration > 0


def test_song_list_similar_reuses_watch_playlist_normalization():
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
