from enum import Enum
from typing import Optional, Union, List

from feeluown_ytmusic.consts import HEADER_FILE
from feeluown_ytmusic.models import YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo, \
    YtmusicSearchPlaylist, YtmusicSearchBase, YtmusicDispatcher, ArtistInfo, UserInfo
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


class YtmusicService:
    def __init__(self):
        if HEADER_FILE.exists():
            self.api = YTMusic(HEADER_FILE)
        else:
            self.api = YTMusic()

    def search(self, keywords: str, t: Optional[YtmusicType], scope: Optional[YtmusicScope], page_size: int = 20) \
            -> List[Union[YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo,
                          YtmusicSearchPlaylist, YtmusicSearchBase]]:
        response = self.api.search(keywords, None if t is None else t.value, None if scope is None else scope.value,
                                   page_size)
        if response is None:
            return []
        return [YtmusicDispatcher.search_result_dispatcher(**data) for data in response]

    def artist_info(self, channel_id: str) -> ArtistInfo:
        return ArtistInfo(**self.api.get_artist(channel_id))

    def artist_albums(self, channel_id: str, params: str) -> List[YtmusicSearchAlbum]:
        response = self.api.get_artist_albums(channel_id, params)
        if response is None:
            return []
        return [YtmusicSearchAlbum(**data) for data in response]

    def user_info(self, channel_id: str) -> UserInfo:
        return UserInfo(**self.api.get_user(channel_id))

    def user_playlists(self, channel_id: str, params: str):
        return self.api.get_user_playlists(channel_id, params)


if __name__ == '__main__':
    import json

    service = YtmusicService()
    print(service.user_info('UCpbIcwkTYzRDIfm1l4E5YMg'))
