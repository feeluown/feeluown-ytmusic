from feeluown.library import BriefSongModel, CollectionType

from fuo_ytmusic.provider import YtmusicProvider


def _build_provider_with_home_sections(sections, expected_limit=None):
    provider = YtmusicProvider()
    expected_limit = expected_limit or provider.HOME_SECTION_LIMIT

    class _ServiceStub:
        def home_sections(self, limit=expected_limit):
            assert limit == expected_limit
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
                    "title": "Song B",
                    "videoId": "vid-b",
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

    assert all(isinstance(song, BriefSongModel) for song in songs)
    assert [song.identifier for song in songs] == ["vid-a", "vid-b"]
    assert songs[0].title == "Song A"
    assert songs[1].title == "Song B"


def test_rec_list_collections_preserves_sections():
    sections = [
        {
            "title": "Quick picks",
            "contents": [
                {
                    "title": "Song A",
                    "videoId": "vid-a",
                    "artists": [{"name": "Artist A", "id": "ar-a"}],
                },
                {
                    "title": "Song B",
                    "videoId": "vid-b",
                },
            ],
        },
        {
            "title": "Daily mixes",
            "contents": [
                {
                    "title": "Mix 1",
                    "playlistId": "PL-1",
                    "author": [{"name": "YouTube Music"}],
                }
            ],
        },
        {
            "title": "Recommended albums",
            "contents": [
                {
                    "title": "Album A",
                    "browseId": "MPREb_album_a",
                    "artists": [{"name": "Artist A", "id": "ar-a"}],
                    "thumbnails": [{"url": "https://example.com/al-a.jpg"}],
                }
            ],
        },
        {
            "title": "Recommended videos",
            "contents": [
                {
                    "title": "Video A",
                    "videoId": "video-a",
                    "views": "10K",
                    "artists": [{"name": "Artist A", "id": "ar-a"}],
                    "duration": "3:20",
                }
            ],
        },
        {
            "title": "Mixed for you",
            "contents": [
                {
                    "title": "My Mix",
                    "playlistId": "RDCLAK5uy_mix_1",
                    "thumbnails": [{"url": "https://example.com/mix-1.jpg"}],
                }
            ],
        },
    ]
    provider = _build_provider_with_home_sections(sections)

    collections = provider.rec_list_collections()

    assert [c.name for c in collections] == [
        "Quick picks",
        "Daily mixes",
        "Recommended albums",
        "Recommended videos",
        "Mixed for you",
    ]
    assert [c.type_ for c in collections] == [
        CollectionType.only_songs,
        CollectionType.only_playlists,
        CollectionType.only_albums,
        CollectionType.only_videos,
        CollectionType.only_playlists,
    ]
    assert [m.identifier for m in collections[0].models] == ["vid-a", "vid-b"]
    assert [m.identifier for m in collections[1].models] == ["PL-1"]
    assert [m.identifier for m in collections[2].models] == ["MPREb_album_a"]
    assert [m.identifier for m in collections[3].models] == ["video-a"]
    assert [m.identifier for m in collections[4].models] == ["RDCLAK5uy_mix_1"]


def test_rec_list_daily_playlists_extracts_and_deduplicates():
    sections = [
        {
            "title": "Daily mixes",
            "contents": [
                {
                    "title": "Mix 1",
                    "playlistId": "PL-1",
                    "description": "desc",
                    "count": "1,234 songs",
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
    assert playlists[0].play_count == 1234


def test_rec_list_daily_songs_dedup_across_sections():
    sections = [
        {
            "title": "Quick picks A",
            "contents": [
                {"title": "Song A", "videoId": "vid-a"},
                {"title": "Song B", "videoId": "vid-b"},
            ],
        },
        {
            "title": "Quick picks B",
            "contents": [
                {"title": "Song A duplicate", "videoId": "vid-a"},
                {"title": "Song C", "videoId": "vid-c"},
            ],
        },
    ]
    provider = _build_provider_with_home_sections(sections)

    songs = provider.rec_list_daily_songs()

    assert [song.identifier for song in songs] == ["vid-a", "vid-b", "vid-c"]


def test_rec_list_collections_skips_none_items():
    sections = [
        {
            "title": "Quick picks",
            "contents": [None, {"title": "Song A", "videoId": "vid-a"}],
        }
    ]
    provider = _build_provider_with_home_sections(sections)

    collections = provider.rec_list_collections()

    assert len(collections) == 1
    assert collections[0].type_ == CollectionType.only_songs
    assert [m.identifier for m in collections[0].models] == ["vid-a"]


def test_rec_list_collections_supports_mixed_section():
    sections = [
        {
            "title": "For you",
            "contents": [
                {"title": "Song A", "videoId": "vid-a"},
                {
                    "title": "Mix A",
                    "playlistId": "RD_mix_a",
                    "videoId": "seed-video",
                    # No artists/album -> should be treated as playlist-like mix card.
                },
            ],
        }
    ]
    provider = _build_provider_with_home_sections(sections)

    collections = provider.rec_list_collections()

    assert [c.name for c in collections] == [
        "For you · Songs",
        "For you · Playlists",
    ]
    assert [c.type_ for c in collections] == [
        CollectionType.only_songs,
        CollectionType.only_playlists,
    ]
    assert [m.identifier for m in collections[0].models] == ["vid-a"]
    assert [m.identifier for m in collections[1].models] == ["RD_mix_a"]


def test_rec_list_daily_returns_empty_when_home_sections_failed():
    provider = YtmusicProvider()

    class _ServiceStub:
        def home_sections(self, limit=6):
            raise RuntimeError("boom")

    provider.service = _ServiceStub()

    assert provider.rec_list_daily_songs() == []
    assert provider.rec_list_daily_playlists() == []


def test_rec_list_collections_supports_limit_parameter():
    sections = [
        {
            "title": "Quick picks",
            "contents": [{"title": "Song A", "videoId": "vid-a"}],
        }
    ]
    provider = _build_provider_with_home_sections(sections, expected_limit=3)

    collections = provider.rec_list_collections(limit=3)

    assert len(collections) == 1
    assert collections[0].type_ == CollectionType.only_songs
