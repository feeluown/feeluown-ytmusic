import logging
from typing import List, Optional

from feeluown.excs import NoUserLoggedIn, ProviderIOError
from feeluown.library import (
    AbstractProvider,
    ProviderV2,
    SongModel,
    VideoModel,
    BriefVideoModel,
    BriefUserModel,
    BriefPlaylistModel,
    PlaylistModel,
    ModelNotFound,
    UserModel,
)
from feeluown.media import Quality, Media, VideoAudioManifest
from feeluown.library import SearchType, SimpleSearchResult
from feeluown.library.model_protocol import BriefSongProtocol
from feeluown.utils.dispatch import Signal
from yt_dlp import YoutubeDL, DownloadError

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.models import Categories, YtmusicWatchPlaylistSong
from fuo_ytmusic.service import YtmusicService, YtmusicType, YtmusicPrivacyStatus

logger = logging.getLogger(__name__)


class YtmusicProvider(AbstractProvider, ProviderV2):
    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()
        self.current_user_changed = Signal()
        self._user = None
        self._http_proxy = ""

        self._default_ytdl_opts = {
            "logger": logger,
            "socket_timeout": 2,
            "extractor_retries": 0,  # reduce retry
        }
        self._default_audio_ytdl_opts = {
            # The following two options may be only valid for select_audio API.
            # Remove these two options if needed.
            "format": "m4a/bestaudio/best",
            **self._default_ytdl_opts,
        }
        self._default_video_ytdl_opts = {
            **self._default_ytdl_opts,
        }

    def setup_http_proxy(self, http_proxy):
        self._http_proxy = http_proxy
        self.service.setup_http_proxy(http_proxy)

    def setup_http_timeout(self, timeout):
        self.service.setup_timeout(timeout)
        self._default_ytdl_opts["socket_timeout"] = timeout

    # noinspection PyPep8Naming
    class meta:
        identifier = "ytmusic"
        name = "YouTube Music"

    @property
    def identifier(self):
        return self.meta.identifier

    @property
    def name(self):
        return self.meta.name

    def auto_login(self):
        if HEADER_FILE.exists():
            logger.info("Try to auto login with header file")
            user = self.try_get_user_with_headerfile()
            if user is None:
                logger.info("Auto login failed")
                return
            self.auth(user)
            self.current_user_changed.emit(user)
        else:
            logger.info("No header file found, skip auto login")

    def try_get_user_with_headerfile(self):
        if HEADER_FILE.exists():
            self.service.reinitialize_by_headerfile(HEADER_FILE)
            user = self.user_get("")
            return user
        return None

    def has_current_user(self) -> bool:
        return self._user is not None

    def get_current_user(self):
        if not self._user:
            raise NoUserLoggedIn
        return self._user

    def user_get(self, identifier):
        # HACK: empty string means the current user.
        if identifier == "":
            try:
                info = self.service.api.get_account_info()
            except Exception as e:
                raise ProviderIOError(f"get current account info failed: {e}")
            return UserModel(
                identifier="",
                source=self.meta.identifier,
                name=info["accountName"],
                avatar_url=info["accountPhotoUrl"],
            )

        user = self.service.user_info(identifier)
        return BriefUserModel(
            identifier=identifier,
            source=self.meta.identifier,
            name=user.name,
        )

    def current_user_list_playlists(self):
        playlists = self.service.library_playlists(100)
        # HACK: FeelUOwn fetches playlists in two places:
        # 1. current_user_list_playlists
        # 2. current_user_fav_create_playlists_rd
        # We cache the playlists in current_user_list_playlists, so that we can
        # avoid fetching playlists in current_user_fav_create_playlists_rd.
        self._user.cache_set("playlists", playlists, ttl=10)
        user_playlists = []
        for playlist in [p.v2_brief_model() for p in playlists]:
            # HACK: use name to filter playlists, because the user identifier
            # may be unknown.
            if playlist.creator_name == self._user.name:
                user_playlists.append(playlist)
        return user_playlists

    def current_user_fav_create_songs_rd(self):
        songs = self.service.library_songs(100)
        return [song.v2_model() for song in songs]

    def current_user_fav_create_artists_rd(self):
        artists = self.service.library_subscription_artists(100)
        return [artist.v2_brief_model() for artist in artists]

    def current_user_fav_create_albums_rd(self):
        albums = self.service.library_albums(100)
        return [album.v2_brief_model() for album in albums]

    def current_user_fav_create_playlists_rd(self) -> List[BriefPlaylistModel]:
        playlists, exist = self._user.cache_get("playlists")
        if not exist:
            playlists = self.service.library_playlists(100)
        user_fav_playlists = []
        for playlist in [p.v2_brief_model() for p in playlists]:
            if playlist.creator_name != self._user.name:
                user_fav_playlists.append(playlist)
        return user_fav_playlists

    def create_playlist(
        self,
        title: str,
        description: str,
        privacy_status: YtmusicPrivacyStatus,
        video_ids: List[str] = None,
        source_playlist: str = None,
    ) -> bool:
        return self.service.create_playlist(
            title, description, privacy_status, video_ids, source_playlist
        )

    def playlist_info(self, identifier) -> PlaylistModel:
        return self.service.playlist_info(identifier, limit=0).v2_model()

    def add_playlist_item(self, identifier, song_id) -> bool:
        result = self.service.add_playlist_items(identifier, [song_id])
        return result.status == "STATUS_SUCCEEDED"

    def remove_playlist_item(self, identifier, song_id, set_song_id) -> bool:
        return (
            self.service.remove_playlist_items(
                identifier,
                [
                    {
                        "videoId": song_id,
                        "setVideoId": set_song_id,
                    }
                ],
            )
            == "STATUS_SUCCEEDED"
        )

    def category_playlists(self, params):
        playlists = self.service.category_playlists(params)
        return [p.model() for p in playlists]

    def categories(self) -> List[Categories]:
        return self.service.categories()

    def search(self, keyword, type_, *args, **kwargs):
        type_ = SearchType.parse(type_)
        ytmusic_type = YtmusicType.parse(type_)
        results = self.service.search(keyword, ytmusic_type)
        model = SimpleSearchResult(q=keyword)
        if results:
            try:
                results[0].v2_model
            except AttributeError:
                models = [r.v2_brief_model() for r in results]
            else:
                # Try to use SongModel instead of BriefSongModel,
                # because there is no way to implement song_get.
                models = [r.v2_model() for r in results]
        else:
            models = []
        setattr(model, ytmusic_type.value, models)
        return model

    def song_list_quality(self, song) -> List[Quality.Audio]:
        return [Quality.Audio.sq]

        id_ = song.identifier
        song_ = self.service.song_info(id_)
        return song_.list_formats() if song_ is not None else []

    def song_get_media(self, song: SongModel, quality: Quality.Audio) -> Optional[Media]:
        ytdl_opts = {}
        ytdl_opts.update(self._default_audio_ytdl_opts)
        # Only set proxy if it is nonempty.
        # Ytdl can make use of system proxy when proxy is not set.
        if self._http_proxy:
            ytdl_opts["proxy"] = self._http_proxy
        url = self.song_get_web_url(song)
        with YoutubeDL(ytdl_opts) as inner:
            try:
                info = inner.extract_info(url, download=False)
            except DownloadError:  # noqa
                logger.warning(f"extract_info failed for {url}")
                raise ProviderIOError("yt-dlp extract info failed", provider=self)
            media_url = info["url"]
            if media_url:
                # NOTE(cosven): do not set http headers, otherwise it can't play.
                # Tested with 'https://music.youtube.com/watch?v=vKwowKeEv5w'
                return Media(
                    media_url,
                    format=info["ext"],
                    bitrate=int(info["abr"] or 0),
                    http_proxy=self._http_proxy,
                )
            return None

    def song_get_web_url(self, song) -> str:
        return f"https://music.youtube.com/watch?v={song.identifier}"

    def song_get(self, identifier):
        # ytmusicapi has not api to get song detail.
        # hack(cosven): we use get_watch_playlist to try to get song detail.
        # It works for song like '如愿-王菲'.
        result = self.service.api.get_watch_playlist(identifier)
        songs = [
            YtmusicWatchPlaylistSong(**track).v2_model() for track in result["tracks"]
        ]
        for song in songs:
            if song.identifier == identifier:
                return song
        # I think this branch should not be reached (in most cases).
        return ModelNotFound(f"song:{identifier} not found")

    def song_list_similar(self, song):
        result = self.service.api.get_watch_playlist(song.identifier)
        songs = [
            YtmusicWatchPlaylistSong(**track).v2_model()
            for track in result["tracks"]
            if track["videoId"] != song.identifier
        ]
        return songs

    def album_get(self, identifier):
        album_info = self.service.album_info(identifier)
        return album_info.v2_model_with_identifier(identifier)

    def artist_get(self, identifier):
        return self.service.artist_info(identifier).v2_model(identifier)

    def playlist_get(self, identifier):
        return self.service.playlist_info(identifier).v2_model()

    def playlist_create_songs_rd(self, playlist):
        playlist_info = self.service.playlist_info(playlist.identifier)
        return playlist_info.reader(self)

    def playlist_add_song(self, playlist, song):
        if playlist.identifier == "LM":
            return False
        return self.add_playlist_item(playlist.identifier, song.identifier)

    # playlist.set_id_map is not currently maintained.
    #
    # def playlist_remove_song(self, playlist, song):
    #     song_id = song.identifier
    #     if playlist.identifier == 'LM':
    #         return False
    #     set_id = playlist.set_id_map.get(song_id)
    #     if set_id is None:
    #         return False
    #     return self.remove_playlist_item(self.identifier, song_id, set_id)

    def artist_create_songs_rd(self, artist):
        artist_info = self.service.artist_info(artist.identifier)
        if artist_info.songs.browseId is None:
            # results may also be none.
            # for example: channelId=UCGSXa1Ve1FswQxtwarGi-Vg
            return [song.v2_model() for song in artist_info.songs.results or []]
        playlist_info = self.service.playlist_info(artist_info.songs.browseId)
        return playlist_info.reader(self)

    def artist_create_albums_rd(self, artist):
        artist_info = self.service.artist_info(artist.identifier)
        # Sometimes, the artist only has few albums, read them from results.
        if artist_info.albums.browseId is None:
            albums = artist_info.albums.results
        else:
            albums = self.service.artist_albums(
                artist_info.albums.browseId, artist_info.albums.params
            )
        return [album.v2_brief_model() for album in albums]

    def video_list_quality(self, video) -> List[Quality.Video]:
        return [Quality.Video.sd]

        id_ = video.identifier
        song_ = self.service.song_info(id_)
        return song_.list_video_formats() if song_ is not None else []

    def video_get(self, identifier):
        song = self.song_get(identifier)
        return VideoModel(
            identifier=song.identifier,
            source=song.source,
            title=song.title,
            artists=song.artists,
            duration=song.duration,
            cover=song.pic_url,
        )

    def video_get_web_url(self, video) -> str:
        return f"https://youtube.com/watch?v={video.identifier}"

    def video_get_media(self, video, quality) -> Optional[Media]:
        ytdl_opts = {}
        ytdl_opts.update(self._default_video_ytdl_opts)
        # Only set proxy if it is nonempty.
        # Ytdl can make use of system proxy when proxy is not set.
        if self._http_proxy:
            ytdl_opts["proxy"] = self._http_proxy
        url = self.video_get_web_url(video)

        audio_candidates = []  # [(url, abr)]  abr: average bitrate
        video_candidates = []  # [(url, width)]
        with YoutubeDL(ytdl_opts) as inner:
            try:
                info = inner.extract_info(url, download=False)
            except DownloadError as e:  # noqa
                logger.warning(f"extract_info failed for {url}")
                raise ProviderIOError("yt-dlp extract info failed", provider=self)
            for f in info["formats"]:
                if f.get("acodec", "none") not in ("none", None):
                    audio_candidates.append((f["url"], f["abr"]))
                if f.get("vcodec", "none") not in ("none", None) and f.get(
                    "protocol", ""
                ) in ("https", "http"):
                    video_candidates.append((f["url"], f["width"]))
            if not (audio_candidates and video_candidates):
                return None
            audio_candidates = sorted(
                audio_candidates, key=lambda c: c[1] or 0, reverse=True
            )
            video_candidates = sorted(
                video_candidates, key=lambda c: c[1] or 0, reverse=True
            )
            # always use the best audio(with highest bitrate)
            audio_url = audio_candidates[0][0]
            # TODO: use policy on video because high-quality video may be slow
            video_url = video_candidates[0][0]
            return Media(
                VideoAudioManifest(video_url, audio_url), http_proxy=self._http_proxy
            )

    def song_get_mv(self, song: BriefSongProtocol) -> BriefVideoModel:
        return BriefVideoModel(
            identifier=song.identifier,
            source=song.source,
            title=song.title,
            artists_name=song.artists_name,
            duration_ms=song.duration_ms,
        )

    def upload_song(self, path: str) -> bool:
        return self.service.upload_song(path) == "STATUS_SUCCEEDED"

    def delete_uploaded_song(self, entity_id: str) -> bool:
        return self.service.delete_upload_song(entity_id) == "STATUS_SUCCEEDED"


provider = YtmusicProvider()
