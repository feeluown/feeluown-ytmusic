import logging
import ntpath
import os
import sys
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
    YtmusicHistorySong, PlaylistAddItemResponse
from ytmusicapi import YTMusic as YTMusicBase
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


class YtmusicPrivacyStatus(Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'
    UNLISTED = 'UNLISTED'

    # noinspection PyTypeChecker
    @classmethod
    def parse(cls, type_: str) -> 'YtmusicPrivacyStatus':
        return cls._value2member_map_.get(type_)


class YtmusicScope(Enum):
    li = 'library'
    up = 'uploads'


class YTMusic(YTMusicBase):
    class IterableToFileAdapter(object):
        def __init__(self, iterable):
            self.iterator = iter(iterable)
            self.length = len(iterable)

        def read(self, size=-1):  # TBD: add buffer for `len(data) > size` case
            return next(self.iterator, b'')

        def __len__(self):
            return self.length

    class ChunckedUpload(object):
        def __init__(self, filename, chunksize=1 << 6):
            self.filename = filename
            self.chunksize = chunksize
            self.totalsize = os.path.getsize(filename)
            self.readsofar = 0

        def __iter__(self):
            with open(self.filename, 'rb') as file:
                while True:
                    data = file.read(self.chunksize)
                    if not data:
                        sys.stdout.write("\n")
                        break
                    self.readsofar += len(data)
                    percent = self.readsofar * 1e2 / self.totalsize
                    sys.stdout.write("\rUploading: {percent:3.0f}%".format(percent=percent))
                    yield data

        def __len__(self):
            return self.totalsize

    def upload_song_progress(self, filepath: str) -> Union[str, requests.Response]:
        """
        Uploads a song to YouTube Music

        :param filepath: Path to the music file (mp3, m4a, wma, flac or ogg)
        :return: Status String or full response
        """
        self._check_auth()
        if not os.path.isfile(filepath):
            raise Exception("The provided file does not exist.")

        supported_filetypes = ["mp3", "m4a", "wma", "flac", "ogg"]
        if os.path.splitext(filepath)[1][1:] not in supported_filetypes:
            raise Exception(
                "The provided file type is not supported by YouTube Music. Supported file types are "
                + ', '.join(supported_filetypes))

        headers = self.headers.copy()
        upload_url = "https://upload.youtube.com/upload/usermusic/http?authuser=0"
        filesize = os.path.getsize(filepath)
        body = ("filename=" + ntpath.basename(filepath)).encode('utf-8')
        headers.pop('content-encoding', None)
        headers['content-type'] = 'application/x-www-form-urlencoded;charset=utf-8'
        headers['X-Goog-Upload-Command'] = 'start'
        headers['X-Goog-Upload-Header-Content-Length'] = str(filesize)
        headers['X-Goog-Upload-Protocol'] = 'resumable'
        response = requests.post(upload_url, data=body, headers=headers, proxies=self.proxies)
        headers['X-Goog-Upload-Command'] = 'upload, finalize'
        headers['X-Goog-Upload-Offset'] = '0'
        upload_url = response.headers['X-Goog-Upload-URL']
        response = requests.post(upload_url, data=YTMusic.IterableToFileAdapter(YTMusic.ChunckedUpload(filepath)),
                                 headers=headers, proxies=self.proxies)
        if response.status_code == 200:
            return 'STATUS_SUCCEEDED'
        else:
            return response


class YtmusicService(metaclass=Singleton):
    def __init__(self, config=None):
        self._session: Optional[requests.Session] = None
        self._api: Optional[YTMusic] = None
        self._js = ""
        self._cipher = None
        self._signature_timestamp = 0
        self.setup(config)

    @staticmethod
    def _do_logging(r: Response, *_, **__):
        logger.debug(f'[ytmusic] Requesting: [{r.request.method.upper()}] {r.url}; '
                     f'Response: [{r.status_code}] {len(r.content)} bytes.')

    @property
    def api(self):
        if self._api is None:
            logger.info('initializing ytmusic')
            if HEADER_FILE.exists():
                self._api = YTMusic(HEADER_FILE, requests_session=self._session, language='zh_CN')
            else:
                self._api = YTMusic(requests_session=self._session, language='zh_CN')
            self._signature_timestamp = self._api.get_signatureTimestamp()
        return self._api

    def setup(self, config=None):
        del self._session
        self._session = requests.Session()
        if config is not None and hasattr(config, 'YTM_HTTP_PROXY') and config.YTM_HTTP_PROXY != '':
            self._session.proxies = {
                'http': 'http://' + config.YTM_HTTP_PROXY,
                'https': 'http://' + config.YTM_HTTP_PROXY
            }
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
    def categories(self) -> List[Categories]:
        return [Categories(key=k, value=v) for k, v in self.api.get_mood_categories().items()]

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

    def create_playlist(self, title: str, description: str, privacy_status: YtmusicPrivacyStatus,
                        video_ids: List[str] = None, source_playlist: str = None) -> bool:
        response = self.api.create_playlist(title, description, privacy_status.value, video_ids, source_playlist)
        if not isinstance(response, str):
            return False
        return True

    def add_playlist_items(self, playlist_id: str, video_ids: List[str] = None, source_playlist_id: str = None) \
            -> PlaylistAddItemResponse:
        return PlaylistAddItemResponse(**self.api.add_playlist_items(playlist_id, video_ids, source_playlist_id))

    def remove_playlist_items(self, playlist_id: str, video_ids: List[dict]) -> Optional[str]:
        # STATUS_SUCCEEDED STATUS_FAILED
        return self.api.remove_playlist_items(playlist_id, video_ids)

    def library_upload_songs(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicLibrarySong]:
        response = self.api.get_library_upload_songs(limit)
        return [YtmusicLibrarySong(**data) for data in response]

    def library_upload_artists(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicLibraryArtist]:
        response = self.api.get_library_upload_artists(limit)
        return [YtmusicLibraryArtist(**data) for data in response]

    def library_upload_albums(self, limit: int = GLOBAL_LIMIT) -> List[YtmusicSearchAlbum]:
        response = self.api.get_library_upload_albums(limit)
        return [YtmusicSearchAlbum(**data) for data in response]

    def upload_song(self, file: str) -> str:
        # STATUS_SUCCEEDED
        return self.api.upload_song_progress(file)

    def delete_upload_song(self, entity_id: str) -> str:
        # STATUS_SUCCEEDED
        return self.api.delete_upload_entity(entity_id)

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
    # print(service.upload_song('/home/bruce/Music/阿梓 - 呼吸决定.mp3'))
    print(service.api.delete_upload_entity('t_po_CJT896eTt_a5swEQwrmdzf7_____AQ'))
