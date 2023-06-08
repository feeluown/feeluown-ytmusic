import logging

from feeluown.library import SearchType

from fuo_ytmusic import service
from fuo_ytmusic.models import YtmusicSearchSong, YtmusicSearchAlbum


class TestService:
    def setup(self):
        service.logger.addHandler(logging.StreamHandler())
        service.logger.setLevel(logging.DEBUG)
        self.service = service.YtmusicService()

    def teardown(self):
        del self.service

    def test_ytmusic_type(self):
        assert service.YtmusicType.parse(SearchType.so) == service.YtmusicType.so
        assert service.YtmusicType.parse(SearchType.al) == service.YtmusicType.al
        assert service.YtmusicType.parse(SearchType.ar) == service.YtmusicType.ar
        assert service.YtmusicType.parse(SearchType.pl) == service.YtmusicType.pl
        assert service.YtmusicType.parse(SearchType.vi) == service.YtmusicType.vi

    def test_search_song(self):
        result = self.service.search('21 Guns', service.YtmusicType.so)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchSong) for r in result)

    def test_search_album(self):
        result = self.service.search('ALIN', service.YtmusicType.al)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchAlbum) for r in result)

    def test_stream_url(self):
        result = self.service.stream_url('U0XcqF7rqHk', 251)
        assert isinstance(result, str)
        assert result != ''
