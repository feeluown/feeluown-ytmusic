import logging

from feeluown.library import SearchType

from fuo_ytmusic import service
from fuo_ytmusic.models import YtmusicSearchAlbum, YtmusicSearchSong


class TestService:
    def setup_method(self):
        service.logger.addHandler(logging.StreamHandler())
        service.logger.setLevel(logging.DEBUG)
        self.service = service.YtmusicService()

    def teardown_method(self):
        del self.service

    def test_ytmusic_type(self):
        assert service.YtmusicType.parse(SearchType.so) == service.YtmusicType.so
        assert service.YtmusicType.parse(SearchType.al) == service.YtmusicType.al
        assert service.YtmusicType.parse(SearchType.ar) == service.YtmusicType.ar
        assert service.YtmusicType.parse(SearchType.pl) == service.YtmusicType.pl
        assert service.YtmusicType.parse(SearchType.vi) == service.YtmusicType.vi

    def test_search_song(self):
        self.service._api = _StubApi(
            [
                {
                    "category": "Songs",
                    "resultType": "song",
                    "title": "21 Guns",
                    "album": {"id": "ALB1", "name": "21st Century Breakdown"},
                    "feedbackTokens": {},
                    "videoId": "VID1",
                    "isAvailable": True,
                    "isExplicit": False,
                    "artists": [{"id": "AR1", "name": "Green Day"}],
                    "thumbnails": [{"url": "https://example.com/1.jpg", "width": 100, "height": 100}],
                    "duration": "3:50",
                }
            ]
        )
        result = self.service.search('21 Guns', service.YtmusicType.so)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchSong) for r in result)

    def test_search_album(self):
        self.service._api = _StubApi(
            [
                {
                    "category": "Albums",
                    "resultType": "album",
                    "title": "ALIN",
                    "type": "Album",
                    "year": "2020",
                    "browseId": "ALB2",
                    "isExplicit": False,
                    "artists": [{"id": "AR2", "name": "A-Lin"}],
                    "thumbnails": [{"url": "https://example.com/2.jpg", "width": 100, "height": 100}],
                }
            ]
        )
        result = self.service.search('ALIN', service.YtmusicType.al)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchAlbum) for r in result)


class _StubApi:
    def __init__(self, payload):
        self._payload = payload

    def search(self, *_args, **_kwargs):
        return list(self._payload)
