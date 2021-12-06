import logging
from datetime import timedelta
from enum import Enum
from functools import partial
from typing import Optional, Union, List
from urllib.parse import unquote

import cachetools.keys
import requests

from feeluown.models import SearchType
from pytube.cipher import Cipher
from requests import Response
from pytube import extract

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.helpers import Singleton
from fuo_ytmusic.models import YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo, \
    YtmusicSearchPlaylist, YtmusicSearchBase, YtmusicDispatcher, ArtistInfo, UserInfo, AlbumInfo, \
    SongInfo, Categories, PlaylistNestedResult, TopCharts, YtmusicLibrarySong, YtmusicLibraryArtist, PlaylistInfo, \
    YtmusicHistorySong
from ytmusicapi import YTMusic
from cachetools.func import ttl_cache

CACHE_TTL = timedelta(minutes=10).seconds
CACHE_SIZE = 1
GLOBAL_LIMIT = 20

logger = logging.getLogger(__name__)


class YtmusicType(Enum):
    so = 'songs'
    vi = 'videos'
    ar = 'artists'
    al = 'albums'
    pl = 'playlists'

    # noinspection PyTypeChecker
    @classmethod
    def parse(cls, type_: SearchType) -> 'YtmusicType':
        return cls._value2member_map_.get(type_.value + 's')


class YtmusicScope(Enum):
    li = 'library'
    up = 'uploads'


class YtmusicService(metaclass=Singleton):
    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._api: Optional[YTMusic] = None
        self._js = ""
        self._cipher = None
        self._signature_timestamp = 0
        self.setup()

    @staticmethod
    def _do_logging(r: Response, *_, **__):
        logger.debug(f'[ytmusic] Requesting: [{r.request.method.upper()}] {r.url}; '
                     f'Response: [{r.status_code}] {len(r.content)} bytes.')

    @property
    def api(self):
        if self._api is None:
            logger.info('initializing ytmusic')
            if HEADER_FILE.exists():
                self._api = YTMusic(HEADER_FILE, requests_session=self._session)
            else:
                self._api = YTMusic(requests_session=self._session)
            self._signature_timestamp = self._api.get_signatureTimestamp()
        return self._api

    def setup(self):
        del self._session
        self._session = requests.Session()
        self._session.hooks['response'].append(self._do_logging)

    def search(self, keywords: str, t: Optional[YtmusicType], scope: YtmusicScope = None,
               page_size: int = GLOBAL_LIMIT) \
            -> List[Union[YtmusicSearchSong, YtmusicSearchAlbum, YtmusicSearchArtist, YtmusicSearchVideo,
                          YtmusicSearchPlaylist, YtmusicSearchBase]]:
        response = self.api.search(keywords, None if t is None else t.value, None if scope is None else scope.value,
                                   page_size)
        return [YtmusicDispatcher.search_result_dispatcher(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def artist_info(self, channel_id: str) -> ArtistInfo:
        return ArtistInfo(**self.api.get_artist(channel_id))

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def artist_albums(self, channel_id: str, params: str) -> List[YtmusicSearchAlbum]:
        response = self.api.get_artist_albums(channel_id, params)
        return [YtmusicSearchAlbum(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def user_info(self, channel_id: str) -> UserInfo:
        return UserInfo(**self.api.get_user(channel_id))

    def user_playlists(self, channel_id: str, params: str):
        return self.api.get_user_playlists(channel_id, params)

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def album_info(self, browse_id: str) -> AlbumInfo:
        return AlbumInfo(**self.api.get_album(browse_id))

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def song_info(self, video_id: str) -> SongInfo:
        return SongInfo(**self.api.get_song(video_id, self._signature_timestamp))

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def categories(self) -> Categories:
        return Categories(**self.api.get_mood_categories())

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def category_playlists(self, params: str) -> List[PlaylistNestedResult]:
        response = self.api.get_mood_playlists(params)
        return [PlaylistNestedResult(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def get_charts(self, country: str = 'ZZ') -> TopCharts:
        # temp workaround for ytmusicapi#236
        # sees: https://github.com/sigma67/ytmusicapi/issues/236
        auth = self.api.auth
        self.api.auth = None
        response = self.api.get_charts(country)
        self.api.auth = auth
        return TopCharts(**response)

    def library_playlists(self, limit: int = GLOBAL_LIMIT) -> List[PlaylistNestedResult]:
        response = self.api.get_library_playlists(limit)
        return [PlaylistNestedResult(**data) for data in response]

    def library_songs(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicLibrarySong]:
        response = self.api.get_library_songs(limit)
        return [YtmusicLibrarySong(**data) for data in response]

    def library_albums(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicSearchAlbum]:
        response = self.api.get_library_albums(limit)
        return [YtmusicSearchAlbum(**data) for data in response]

    def library_artists(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicLibraryArtist]:
        response = self.api.get_library_artists(limit)
        return [YtmusicLibraryArtist(**data) for data in response]

    def library_subscription_artists(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicLibraryArtist]:
        response = self.api.get_library_subscriptions(limit)
        return [YtmusicLibraryArtist(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def playlist_info(self, playlist_id: str, limit: int = GLOBAL_LIMIT) -> PlaylistInfo:
        return PlaylistInfo(**self.api.get_playlist(playlist_id, limit))

    def liked_songs(self, limit: int = GLOBAL_LIMIT) -> PlaylistInfo:
        return PlaylistInfo(**self.api.get_liked_songs(limit))

    def history(self) -> List[YtmusicHistorySong]:
        response = self.api.get_history()
        return [YtmusicHistorySong(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def stream_url(self, video_id: str, format_code: int) -> Optional[str]:
        song_info = self.song_info(video_id)
        formats = song_info.streamingData.adaptiveFormats
        for f in formats:
            if int(f.itag) == format_code:
                return self._get_stream_url(f, video_id)
        return None

    def _get_stream_url(self, f: SongInfo.StreamingData.Format, video_id: str, retry=True) -> Optional[str]:
        if f.url is not None and f.url != '':
            return f.url
        sig_ch = f.signatureCipher
        sig_ex = sig_ch.split('&')
        res = dict({'s': '', 'url': ''})
        for sig in sig_ex:
            for key in res:
                if sig.find(key + "=") >= 0:
                    res[key] = unquote(sig[len(key + "="):])
        if self._js == "":
            self._get_cipher(video_id)
        signature = self._cipher.get_signature(ciphered_signature=res['s'])
        _url = res['url'] + "&sig=" + signature
        if retry:
            r = self._session.head(_url)
            if r.status_code == 403:
                logger.info('[ytmusic] update signature timestamp and try again')
                self._signature_timestamp = self._api.get_signatureTimestamp()
            return self._get_stream_url(f, video_id, retry=False)
        return _url

    def _get_cipher(self, video_id: str):
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        embed_html = self._session.get(embed_url).text
        js_url = extract.js_url(embed_html)
        self._js = self._session.get(js_url).text
        self._cipher = Cipher(js=self._js)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    import json

    service = YtmusicService()
    print(service.stream_url('U0XcqF7rqHk', 251))
