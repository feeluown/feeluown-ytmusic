from feeluown.library import BriefPlaylistModel, PlaylistModel

from fuo_ytmusic.provider import YtmusicProvider


def test_toplist_list_extracts_and_deduplicates_playlists():
    provider = YtmusicProvider()
    charts = {
        "daily": [
            {"title": "Daily A", "playlistId": "PL-daily-a"},
            {"title": "Daily duplicate", "playlistId": "PL-shared"},
        ],
        "weekly": [
            {"title": "Weekly A", "playlistId": "PL-weekly-a"},
            {"title": "Weekly duplicate", "playlistId": "PL-shared"},
        ],
        "videos": [
            {"title": "Videos A", "playlistId": "PL-videos-a"},
            {"title": "Ignore missing id"},
            None,
        ],
        "genres": [
            {"title": "Genres A", "playlistId": "PL-genres-a"},
            {"title": "Genres duplicate", "playlistId": "PL-videos-a"},
        ],
        "artists": [{"title": "Artist X"}],
    }

    class _ServiceStub:
        def get_charts(self, country="ZZ"):
            assert country == "ZZ"
            return charts

    provider.service = _ServiceStub()

    toplists = provider.toplist_list()

    assert all(isinstance(each, BriefPlaylistModel) for each in toplists)
    assert [each.identifier for each in toplists] == [
        "PL-daily-a",
        "PL-shared",
        "PL-weekly-a",
        "PL-videos-a",
        "PL-genres-a",
    ]
    assert [each.name for each in toplists] == [
        "Daily A",
        "Daily duplicate",
        "Weekly A",
        "Videos A",
        "Genres A",
    ]


def test_toplist_list_returns_empty_when_fetch_failed():
    provider = YtmusicProvider()

    class _ServiceStub:
        def get_charts(self, country="ZZ"):
            raise RuntimeError("boom")

    provider.service = _ServiceStub()

    assert provider.toplist_list() == []


def test_toplist_get_delegates_to_playlist_info():
    provider = YtmusicProvider()
    expected = PlaylistModel(
        identifier="PL-1",
        source="ytmusic",
        name="Toplist A",
        cover="",
        description="",
    )

    class _PlaylistInfoStub:
        def v2_model(self):
            return expected

    class _ServiceStub:
        def playlist_info(self, identifier):
            assert identifier == "PL-1"
            return _PlaylistInfoStub()

    provider.service = _ServiceStub()

    assert provider.toplist_get("PL-1") is expected
