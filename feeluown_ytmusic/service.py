from datetime import timedelta
from enum import Enum
from typing import Optional, Union, List

import cachetools

from feeluown_ytmusic.consts import HEADER_FILE
from feeluown_ytmusic.models import YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo, \
    YtmusicSearchPlaylist, YtmusicSearchBase, YtmusicDispatcher, ArtistInfo, UserInfo, AlbumInfo, \
    SongInfo
from ytmusicapi import YTMusic
from cachetools import TTLCache

CACHE = TTLCache(maxsize=50, ttl=timedelta(minutes=10).seconds)


class YtmusicType(Enum):
    so = 'songs'
    vi = 'videos'
    ar = 'artists'
    al = 'albums'
    pl = 'playlists'


class YtmusicScope(Enum):
    li = 'library'
    up = 'uploads'


class YtmusicService:
    def __init__(self):
        if HEADER_FILE.exists():
            self.api = YTMusic(HEADER_FILE)
        else:
            self.api = YTMusic()

    def search(self, keywords: str, t: Optional[YtmusicType], scope: YtmusicScope = None, page_size: int = 20) \
            -> List[Union[YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo,
                          YtmusicSearchPlaylist, YtmusicSearchBase]]:
        response = self.api.search(keywords, None if t is None else t.value, None if scope is None else scope.value,
                                   page_size)
        if response is None:
            return []
        return [YtmusicDispatcher.search_result_dispatcher(**data) for data in response]

    @cachetools.cached(cache=CACHE)
    def artist_info(self, channel_id: str) -> ArtistInfo:
        return ArtistInfo(**self.api.get_artist(channel_id))

    def artist_albums(self, channel_id: str, params: str) -> List[YtmusicSearchAlbum]:
        response = self.api.get_artist_albums(channel_id, params)
        if response is None:
            return []
        return [YtmusicSearchAlbum(**data) for data in response]

    @cachetools.cached(cache=CACHE)
    def user_info(self, channel_id: str) -> UserInfo:
        return UserInfo(**self.api.get_user(channel_id))

    def user_playlists(self, channel_id: str, params: str):
        return self.api.get_user_playlists(channel_id, params)

    @cachetools.cached(cache=CACHE)
    def album_info(self, browse_id: str) -> AlbumInfo:
        return AlbumInfo(**self.api.get_album(browse_id))

    @cachetools.cached(cache=CACHE)
    def song_info(self, video_id: str) -> SongInfo:
        return SongInfo(**self.api.get_song(video_id))


if __name__ == '__main__':
    import json

    service = YtmusicService()
    print(service.song_info('1IMmKEKQOOg'))
