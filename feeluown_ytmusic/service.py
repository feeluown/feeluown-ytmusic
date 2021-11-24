from enum import Enum
from typing import Optional, Union, List

from feeluown_ytmusic.consts import HEADER_FILE
from feeluown_ytmusic.models import YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo, \
    YtmusicSearchPlaylist
from ytmusicapi import YTMusic


class YtmusicType(Enum):
    so = 'songs'
    vi = 'videos'
    ar = 'artists'
    al = 'albums'
    pl = 'playlists'


class YtmusicScope(Enum):
    li = 'library'
    up = 'uploads'


YTMUSIC_SEARCH_MAP = {
    YtmusicType.so: YtmusicSearchSong,
    YtmusicType.vi: YtmusicSearchVideo,
    YtmusicType.ar: YtmusicSearchArtist,
    YtmusicType.al: YtmusicSearchAlbum,
    YtmusicType.pl: YtmusicSearchPlaylist,
}


class YtmusicService:
    def __init__(self):
        if HEADER_FILE.exists():
            self.api = YTMusic(HEADER_FILE)
        else:
            self.api = YTMusic()

    def search(self, keywords: str, t: Optional[YtmusicType], scope: Optional[YtmusicScope], page_size: int = 20) \
            -> List[Union[YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo,
                          YtmusicSearchPlaylist, None]]:
        clazz = YTMUSIC_SEARCH_MAP.get(t)
        if clazz is None:
            return []
        response = self.api.search(keywords, None if t is None else t.value, None if scope is None else scope.value,
                                   page_size)
        if response is None:
            return []
        return [clazz(**data) for data in response]


if __name__ == '__main__':
    import json

    service = YtmusicService()
    print(json.dumps(service.search('阿梓', YtmusicType.vi, None, 10)))
