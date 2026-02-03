import json
import logging
import ntpath
import os
import sys
import threading
import time
from http.cookies import SimpleCookie
from datetime import timedelta
from enum import Enum
from functools import partial
from typing import Optional, Union, List

import requests
from ytmusicapi import YTMusic as YTMusicBase
from ytmusicapi.constants import YTM_BASE_API, YTM_DOMAIN
from ytmusicapi.ytmusic import OAuthCredentials
from cachetools.func import ttl_cache
from requests import Response
from feeluown.library import SearchType

from fuo_ytmusic.helpers import Singleton
from fuo_ytmusic.models import (
    YtmusicSearchSong,
    YtmusicSearchAlbum,
    YtmusicSearchArtist,
    YtmusicSearchVideo,
    YtmusicSearchPlaylist,
    YtmusicSearchBase,
    YtmusicDispatcher,
    ArtistInfo,
    UserInfo,
    AlbumInfo,
    SongInfo,
    Categories,
    PlaylistNestedResult,
    TopCharts,
    YtmusicLibrarySong,
    YtmusicLibraryArtist,
    PlaylistInfo,
    YtmusicHistorySong,
    PlaylistAddItemResponse,
)


CACHE_TTL = timedelta(minutes=10).seconds
CACHE_SIZE = 1
GLOBAL_LIMIT = 20

logger = logging.getLogger(__name__)


class YtmusicType(Enum):
    so = "songs"
    vi = "videos"
    ar = "artists"
    al = "albums"
    pl = "playlists"

    # noinspection PyTypeChecker
    @classmethod
    def parse(cls, type_: SearchType) -> "YtmusicType":
        return cls._value2member_map_.get(type_.value + "s")


class YtmusicPrivacyStatus(Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    UNLISTED = "UNLISTED"

    # noinspection PyTypeChecker
    @classmethod
    def parse(cls, type_: str) -> "YtmusicPrivacyStatus":
        return cls._value2member_map_.get(type_)


class YtmusicScope(Enum):
    li = "library"
    up = "uploads"


class YTMusic(YTMusicBase):
    class IterableToFileAdapter(object):
        def __init__(self, iterable):
            self.iterator = iter(iterable)
            self.length = len(iterable)

        def read(self, size=-1):  # TBD: add buffer for `len(data) > size` case
            return next(self.iterator, b"")

        def __len__(self):
            return self.length

    class ChunckedUpload(object):
        def __init__(self, filename, chunksize=1 << 6):
            self.filename = filename
            self.chunksize = chunksize
            self.totalsize = os.path.getsize(filename)
            self.readsofar = 0

        def __iter__(self):
            with open(self.filename, "rb") as file:
                while True:
                    data = file.read(self.chunksize)
                    if not data:
                        sys.stdout.write("\n")
                        break
                    self.readsofar += len(data)
                    percent = self.readsofar * 1e2 / self.totalsize
                    sys.stdout.write(
                        "\rUploading: {percent:3.0f}%".format(percent=percent)
                    )
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
                "The provided file type is not supported by YouTube Music."
                f" Supported file types are {', '.join(supported_filetypes)}"
            )

        headers = self.headers.copy()
        upload_url = "https://upload.youtube.com/upload/usermusic/http?authuser=0"
        filesize = os.path.getsize(filepath)
        body = ("filename=" + ntpath.basename(filepath)).encode("utf-8")
        headers.pop("content-encoding", None)
        headers["content-type"] = "application/x-www-form-urlencoded;charset=utf-8"
        headers["X-Goog-Upload-Command"] = "start"
        headers["X-Goog-Upload-Header-Content-Length"] = str(filesize)
        headers["X-Goog-Upload-Protocol"] = "resumable"
        response = requests.post(
            upload_url, data=body, headers=headers, proxies=self.proxies
        )
        headers["X-Goog-Upload-Command"] = "upload, finalize"
        headers["X-Goog-Upload-Offset"] = "0"
        upload_url = response.headers["X-Goog-Upload-URL"]
        response = requests.post(
            upload_url,
            data=YTMusic.IterableToFileAdapter(YTMusic.ChunckedUpload(filepath)),
            headers=headers,
            proxies=self.proxies,
        )
        if response.status_code == 200:
            return "STATUS_SUCCEEDED"
        else:
            return response


class YtmusicService(metaclass=Singleton):
    def __init__(self):
        self._session = requests.Session()
        self._api: Optional[YTMusic] = None
        self._session.hooks["response"].append(self._do_logging)

        self._signature_timestamp = 0
        self._api_lock = threading.Lock()
        self._account_override = None
        self._forced_gaia_id = None

    @staticmethod
    def _do_logging(r: Response, *_, **__):
        logger.debug(
            f"[ytmusic] Requesting: [{r.request.method.upper()}] {r.url}; "
            f"Response: [{r.status_code}] {len(r.content)} bytes."
        )

    @property
    def api(self) -> YTMusic:
        if self._api is None:
            with self._api_lock:
                if self._api is None:
                    self.reinitialize_by_headerfile()
        return self._api

    def _log_thread(self):
        return f"Thread({threading.get_ident()})"

    def get_signature_timestamp(self):
        return 0

    def reinitialize_by_headerfile(self, headerfile=None):
        options = dict(
            requests_session=self._session,
            language="zh_CN",
            oauth_credentials=OAuthCredentials(
                # In the new version of ytmusicapi, client_id and client_secret
                # are required args.
                #   https://github.com/sigma67/ytmusicapi/pull/688
                # Hardcode the client_id and client_secret to workaround.
                client_id=(
                    "861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68"
                    ".apps.googleusercontent.com"
                ),
                client_secret="SboVhoG9s0rNafixCSGGKXAT",
                session=self._session,
            ),
        )
        # Due to https://github.com/sigma67/ytmusicapi/issues/676,
        # YTMusic does not work in specific cases when auth file is provided.
        # So initialize without auth file when 400 is returned.
        if headerfile is not None and headerfile.exists():
            logger.info("Initializing ytmusic api with headerfile.")
            self._api = YTMusic(str(headerfile), **options)
        else:
            logger.info("Initializing ytmusic api with no headerfile.")
            self._api = YTMusic(**options)

    def setup_http_proxy(self, http_proxy):
        self._session.proxies = {
            "http": http_proxy,
            "https": http_proxy,
        }

    def setup_timeout(self, timeout):
        if isinstance(self._session.request, partial):
            request = self._session.request.func
        else:
            request = self._session.request
        self._session.request = partial(request, timeout=timeout)

    def search(
        self,
        keywords: str,
        t: Optional[YtmusicType],
        scope: YtmusicScope = None,
        page_size: int = GLOBAL_LIMIT,
    ) -> List[
        Union[
            YtmusicSearchSong,
            YtmusicSearchAlbum,
            YtmusicSearchArtist,
            YtmusicSearchVideo,
            YtmusicSearchPlaylist,
            YtmusicSearchBase,
        ]
    ]:
        response = self.api.search(
            keywords,
            None if t is None else t.value,
            None if scope is None else scope.value,
            page_size,
        )
        return [YtmusicDispatcher.search_result_dispatcher(**data) for data in response]

    def get_current_account_info(self) -> dict:
        self.api._check_auth()
        if self._account_override is not None:
            return self._account_override
        fallback_info = self._safe_get_account_menu_info()

        switcher = self._get_account_switcher()
        if switcher is not None:
            items = self._find_account_items(switcher)
            datasync_id = self._extract_datasync_id(switcher)
            selected = self._pick_account_item(
                items, datasync_id, self._forced_gaia_id
            )
            if selected is None:
                fallback_info = self._safe_get_account_menu_info()
                if fallback_info is not None:
                    selected = self._find_account_item_by_name(
                        items, fallback_info.get("accountName")
                    )
            if selected is not None:
                info = self._build_account_info(selected)
                if info is not None:
                    return info

        accounts_list = self._get_accounts_list()
        if accounts_list is not None:
            items = self._find_account_items(accounts_list)
            datasync_id = self._extract_datasync_id(accounts_list)
            selected = self._pick_account_item(
                items, datasync_id, self._forced_gaia_id
            )
            if selected is None and fallback_info is None:
                fallback_info = self._safe_get_account_menu_info()
            if selected is None and fallback_info is not None:
                selected = self._find_account_item_by_name(
                    items, fallback_info.get("accountName")
                )
            if selected is not None:
                info = self._build_account_info(selected)
                if info is not None:
                    return info

        if fallback_info is not None:
            return fallback_info
        raise ValueError("No account info available")

    def list_profiles(self) -> List[dict]:
        switcher = self._get_account_switcher()
        if switcher is None:
            switcher = self._get_accounts_list()
        if switcher is None:
            return []

        items = self._find_account_items(switcher)
        datasync_id = self._extract_datasync_id(switcher)
        profiles = []
        for item in items:
            name = self._extract_text(item.get("accountName"))
            if not name:
                continue
            channel_handle = self._extract_text(item.get("channelHandle"))
            if not channel_handle:
                continue
            profiles.append(
                {
                    "accountName": name,
                    "channelHandle": channel_handle,
                    "accountPhotoUrl": self._extract_thumbnail_url(
                        item.get("accountPhoto")
                    ),
                    "gaiaId": self._extract_obfuscated_gaia_id(item),
                    "isSelected": self._is_item_selected(item, datasync_id),
                }
            )
        return profiles

    def switch_profile(self, account_name: str = None, gaia_id: str = None) -> dict:
        if not account_name and not gaia_id:
            self._set_on_behalf_of_user(None)
            self._account_override = None
            self._forced_gaia_id = None
            self._clear_caches()
            return self.get_current_account_info()

        switcher = self._get_account_switcher()
        if switcher is None:
            switcher = self._get_accounts_list()
        if switcher is None:
            raise ValueError("No account switcher data available")

        items = self._find_account_items(switcher)
        selected = None
        if gaia_id:
            for item in items:
                if self._extract_obfuscated_gaia_id(item) == gaia_id:
                    selected = item
                    break
        else:
            selected = self._find_account_item_by_name(items, account_name)

        if selected is None:
            raise ValueError("Profile not found")

        selected_gaia_id = self._extract_obfuscated_gaia_id(selected)
        self._set_on_behalf_of_user(selected_gaia_id)
        self._forced_gaia_id = selected_gaia_id
        self._account_override = self._build_account_info(selected)
        self._clear_caches()
        return self._account_override

    def _set_on_behalf_of_user(self, gaia_id):
        context = self.api.context.setdefault("context", {})
        user_ctx = context.setdefault("user", {})
        if gaia_id:
            user_ctx["onBehalfOfUser"] = gaia_id
        else:
            user_ctx.pop("onBehalfOfUser", None)

    def _clear_caches(self):
        self.artist_info.cache_clear()
        self.artist_albums.cache_clear()
        self.user_info.cache_clear()
        self.album_info.cache_clear()
        self.categories.cache_clear()
        self.category_playlists.cache_clear()
        self.get_charts.cache_clear()
        self.playlist_info.cache_clear()

    def _get_account_switcher(self):
        response = self._request_account_switcher(
            url="https://music.youtube.com/getAccountSwitcherEndpoint",
            origin=YTM_DOMAIN,
        )
        if self._has_account_items(response):
            return response
        return None

    def _request_account_switcher(self, url, origin):
        try:
            headers = dict(self.api.headers)
            headers["origin"] = origin
            response = self._session.request(
                "GET",
                url,
                headers=headers,
                proxies=self._session.proxies,
                cookies=self.api.cookies,
            )
            response_text = response.text
        except Exception as e:
            logger.debug("account switcher request failed: %s", e)
            return None

        if response.status_code >= 400:
            logger.debug(
                "account switcher request failed with status %s",
                response.status_code,
            )
            return None

        self._update_auth_cookie_from_response(response)

        payload = self._strip_xssi_prefix(response_text)
        try:
            return json.loads(payload)
        except Exception as e:
            logger.debug("account switcher parse failed: %s", e)
            return None

    @staticmethod
    def _strip_xssi_prefix(text):
        if not isinstance(text, str):
            return text
        if text.startswith(")]}'"):
            newline = text.find("\n")
            if newline != -1:
                return text[newline + 1 :]
            return text[4:]
        return text

    def _get_accounts_list(self):
        try:
            response = self.api._send_request("account/accounts_list", {})
        except Exception as e:
            logger.debug("accounts_list api request failed: %s", e)
            response = None
        if self._has_account_items(response):
            return response

        response = self._request_accounts_list(
            client_name="WEB_REMIX",
            origin=YTM_DOMAIN,
            url=f"{YTM_BASE_API}account/accounts_list{self.api.params}",
        )
        if self._has_account_items(response):
            return response

        response = self._request_accounts_list(
            client_name="WEB",
            origin="https://www.youtube.com",
            url="https://www.youtube.com/youtubei/v1/account/accounts_list?alt=json",
        )
        if self._has_account_items(response):
            return response
        return None

    def _request_accounts_list(self, client_name, origin, url):
        try:
            body = {"context": self._build_accounts_list_context(client_name)}
            headers = dict(self.api.headers)
            headers["origin"] = origin
            response = self._session.request(
                "POST",
                url,
                json=body,
                headers=headers,
                proxies=self._session.proxies,
                cookies=self.api.cookies,
            )
            response_text = response.json()
        except Exception as e:
            logger.debug("accounts_list request failed: %s", e)
            return None

        if response.status_code >= 400:
            logger.debug(
                "accounts_list request failed with status %s", response.status_code
            )
            return None
        self._update_auth_cookie_from_response(response)
        return response_text

    def _build_accounts_list_context(self, client_name):
        base_context = self.api.context.get("context", {})
        client = dict(base_context.get("client", {}))
        user = dict(base_context.get("user", {}))
        client["clientName"] = client_name
        if client_name == "WEB" and client.get("clientVersion", "").startswith("1."):
            client["clientVersion"] = "2." + time.strftime("%Y%m%d") + ".00.00"
        return {"client": client, "user": user}

    @staticmethod
    def _find_account_items(data):
        items = []
        if isinstance(data, dict):
            for key in ("accountItem", "accountItemRenderer"):
                item = data.get(key)
                if isinstance(item, dict):
                    items.append(item)
            for value in data.values():
                items.extend(YtmusicService._find_account_items(value))
        elif isinstance(data, list):
            for value in data:
                items.extend(YtmusicService._find_account_items(value))
        return items

    @staticmethod
    def _pick_account_item(items, datasync_id=None, gaia_id=None):
        if gaia_id:
            for item in items:
                if YtmusicService._extract_obfuscated_gaia_id(item) == gaia_id:
                    return item
        for item in items:
            if item.get("isSelected") or item.get("isCurrent") or item.get("isActive"):
                return item
        if datasync_id:
            for item in items:
                if YtmusicService._extract_obfuscated_gaia_id(item) == datasync_id:
                    return item
        return None

    @staticmethod
    def _find_account_item_by_name(items, name):
        if not name:
            return None
        for item in items:
            if YtmusicService._extract_text(item.get("accountName")) == name:
                return item
        return None

    @staticmethod
    def _extract_datasync_id(response):
        if not isinstance(response, dict):
            return None
        response_context = response.get("responseContext", {})
        main_context = response_context.get("mainAppWebResponseContext", {})
        datasync_id = main_context.get("datasyncId")
        if not datasync_id or not isinstance(datasync_id, str):
            return None
        return datasync_id.split("||", 1)[0]

    @staticmethod
    def _extract_obfuscated_gaia_id(item):
        if not isinstance(item, dict):
            return None
        service_endpoint = item.get("serviceEndpoint", {})
        select_endpoint = service_endpoint.get("selectActiveIdentityEndpoint", {})
        tokens = select_endpoint.get("supportedTokens", [])
        if not isinstance(tokens, list):
            return None
        for token in tokens:
            account_state = token.get("accountStateToken")
            if isinstance(account_state, dict):
                obfuscated_id = account_state.get("obfuscatedGaiaId")
                if obfuscated_id:
                    return obfuscated_id
        return None

    @staticmethod
    def _has_account_items(response):
        if response is None:
            return False
        return bool(YtmusicService._find_account_items(response))

    def _safe_get_account_menu_info(self):
        try:
            return self.api.get_account_info()
        except Exception as e:
            logger.debug("account_menu request failed: %s", e)
            return None

    def _update_auth_cookie_from_response(self, response):
        try:
            cookie_header = self.api.headers.get("cookie", "")
        except Exception:
            cookie_header = ""
        if not response.cookies:
            return
        jar = SimpleCookie()
        if cookie_header:
            jar.load(cookie_header)
        for cookie in response.cookies:
            jar[cookie.name] = cookie.value
        new_cookie = "; ".join([f"{m.key}={m.value}" for m in jar.values()])
        if new_cookie:
            self.api._auth_headers["cookie"] = new_cookie

    @staticmethod
    def _extract_text(value):
        if isinstance(value, dict):
            runs = value.get("runs")
            if isinstance(runs, list) and runs:
                text = runs[0].get("text")
                if text:
                    return text
            simple_text = value.get("simpleText")
            if simple_text:
                return simple_text
        if isinstance(value, str):
            return value
        return None

    @staticmethod
    def _build_account_info(item):
        account_name = YtmusicService._extract_text(item.get("accountName"))
        if not account_name:
            return None
        channel_handle = YtmusicService._extract_text(item.get("channelHandle"))
        account_photo_url = YtmusicService._extract_thumbnail_url(
            item.get("accountPhoto")
        )
        return {
            "accountName": account_name,
            "channelHandle": channel_handle,
            "accountPhotoUrl": account_photo_url,
        }

    @staticmethod
    def _extract_thumbnail_url(account_photo):
        if not isinstance(account_photo, dict):
            return None
        thumbnails = account_photo.get("thumbnails")
        if isinstance(thumbnails, list) and thumbnails:
            return thumbnails[0].get("url")
        return None

    @staticmethod
    def _is_item_selected(item, datasync_id=None):
        if item.get("isSelected") or item.get("isCurrent") or item.get("isActive"):
            return True
        if datasync_id:
            return YtmusicService._extract_obfuscated_gaia_id(item) == datasync_id
        return False

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def artist_info(self, channel_id: str) -> ArtistInfo:
        data = self.api.get_artist(channel_id)
        return ArtistInfo(**data)

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
        data = self.api.get_album(browse_id)
        return AlbumInfo(**data)

    def song_info(self, video_id: str) -> SongInfo:
        return SongInfo(**self.api.get_song(video_id, self.get_signature_timestamp()))

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def categories(self) -> List[Categories]:
        return [
            Categories(key=k, value=v) for k, v in self.api.get_mood_categories().items()
        ]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def category_playlists(self, params: str) -> List[PlaylistNestedResult]:
        response = self.api.get_mood_playlists(params)
        return [PlaylistNestedResult(**data) for data in response]

    @ttl_cache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
    def get_charts(self, country: str = "ZZ") -> TopCharts:
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

    def library_subscription_artists(
        self, limit: int = GLOBAL_LIMIT
    ) -> List[YtmusicLibraryArtist]:
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

    def create_playlist(
        self,
        title: str,
        description: str,
        privacy_status: YtmusicPrivacyStatus,
        video_ids: List[str] = None,
        source_playlist: str = None,
    ) -> bool:
        response = self.api.create_playlist(
            title, description, privacy_status.value, video_ids, source_playlist
        )
        if not isinstance(response, str):
            return False
        return True

    def add_playlist_items(
        self,
        playlist_id: str,
        video_ids: List[str] = None,
        source_playlist_id: str = None,
    ) -> PlaylistAddItemResponse:
        return PlaylistAddItemResponse(
            **self.api.add_playlist_items(playlist_id, video_ids, source_playlist_id)
        )

    def remove_playlist_items(
        self, playlist_id: str, video_ids: List[dict]
    ) -> Optional[str]:
        # STATUS_SUCCEEDED STATUS_FAILED
        return self.api.remove_playlist_items(playlist_id, video_ids)

    def library_upload_songs(
        self, limit: int = GLOBAL_LIMIT
    ) -> List[YtmusicLibrarySong]:
        response = self.api.get_library_upload_songs(limit)
        return [YtmusicLibrarySong(**data) for data in response]

    def library_upload_artists(
        self, limit: int = GLOBAL_LIMIT
    ) -> List[YtmusicLibraryArtist]:
        response = self.api.get_library_upload_artists(limit)
        return [YtmusicLibraryArtist(**data) for data in response]

    def library_upload_albums(
        self, limit: int = GLOBAL_LIMIT
    ) -> List[YtmusicSearchAlbum]:
        response = self.api.get_library_upload_albums(limit)
        return [YtmusicSearchAlbum(**data) for data in response]

    def upload_song(self, file: str) -> str:
        # STATUS_SUCCEEDED
        return self.api.upload_song_progress(file)

    def delete_upload_song(self, entity_id: str) -> str:
        # STATUS_SUCCEEDED
        return self.api.delete_upload_entity(entity_id)

    def stream_url(
        self, song_info: SongInfo, video_id: str, format_code: int
    ) -> Optional[str]:
        formats = song_info.streamingData.adaptiveFormats
        for f in formats:
            if int(f.itag) == format_code:
                return self._get_stream_url(f, video_id)
        return None

    def check_stream_url(self, url):
        resp = self._session.head(url)
        return resp.status_code != 403


if __name__ == "__main__":
    # noinspection PyUnresolvedReferences

    service = YtmusicService()
    # print(service.upload_song('/home/bruce/Music/阿梓 - 呼吸决定.mp3'))
    print(service.api.delete_upload_entity("t_po_CJT896eTt_a5swEQwrmdzf7_____AQ"))
