from fuo_ytmusic.provider import YtmusicProvider


def _build_provider_with_home_sections(sections):
    provider = YtmusicProvider()

    class _ServiceStub:
        def home_sections(self, limit=6):
            assert limit == 6
            return sections

    provider.service = _ServiceStub()
    return provider


def test_rec_list_daily_songs_extracts_and_deduplicates():
    sections = [
        {
            "title": "Quick picks",
            "contents": [
                {
                    "title": "Song A",
                    "videoId": "vid-a",
                    "artists": [{"name": "Artist A", "id": "ar-a"}],
                    "album": {"name": "Album A", "id": "al-a"},
                    "thumbnails": [{"url": "https://example.com/a.jpg"}],
                    "duration": "3:10",
                },
                {
                    "title": "Song A duplicate",
                    "videoId": "vid-a",
                    "artists": [{"name": "Artist A", "id": "ar-a"}],
                    "thumbnails": [{"url": "https://example.com/a2.jpg"}],
                    "duration": "3:10",
                },
                {
                    "title": "Playlist only",
                    "playlistId": "PL1",
                },
            ],
        }
    ]
    provider = _build_provider_with_home_sections(sections)

    songs = provider.rec_list_daily_songs()

    assert len(songs) == 1
    assert songs[0].identifier == "vid-a"
    assert songs[0].title == "Song A"


def test_rec_list_daily_playlists_extracts_and_deduplicates():
    sections = [
        {
            "title": "Daily mixes",
            "contents": [
                {
                    "title": "Mix 1",
                    "playlistId": "PL-1",
                    "description": "desc",
                    "count": "12",
                    "author": [{"name": "YouTube Music"}],
                    "thumbnails": [{"url": "https://example.com/p1.jpg"}],
                },
                {
                    "title": "Mix 1 duplicate",
                    "playlistId": "PL-1",
                    "thumbnails": [{"url": "https://example.com/p1_2.jpg"}],
                },
                {
                    "title": "Not a playlist",
                    "videoId": "vid-x",
                    "artists": [{"name": "Artist X", "id": "ar-x"}],
                },
            ],
        }
    ]
    provider = _build_provider_with_home_sections(sections)

    playlists = provider.rec_list_daily_playlists()

    assert len(playlists) == 1
    assert playlists[0].identifier == "PL-1"
    assert playlists[0].name == "Mix 1"
    assert playlists[0].creator_name == "YouTube Music"


def test_rec_list_daily_returns_empty_when_home_sections_failed():
    provider = YtmusicProvider()

    class _ServiceStub:
        def home_sections(self, limit=6):
            raise RuntimeError("boom")

    provider.service = _ServiceStub()

    assert provider.rec_list_daily_songs() == []
    assert provider.rec_list_daily_playlists() == []
