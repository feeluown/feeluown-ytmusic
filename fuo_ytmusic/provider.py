import logging
from urllib.parse import urlparse, parse_qs
from typing import List, Optional

from feeluown.excs import NoUserLoggedIn
from feeluown.library import (
    AbstractProvider, ProviderV2, ProviderFlags as Pf,
    SongModel, VideoModel, BriefVideoModel, BriefUserModel, ModelType,
    BriefPlaylistModel, BriefArtistModel, PlaylistModel, ModelNotFound,
)
from feeluown.media import Quality, Media, VideoAudioManifest, MediaType
from feeluown.library import SearchType, SimpleSearchResult
from feeluown.library.model_protocol import BriefSongProtocol

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.models import Categories, YtBriefUserModel, YtmusicWatchPlaylistSong
from fuo_ytmusic.service import YtmusicService, YtmusicType, YtmusicPrivacyStatus

logger = logging.getLogger(__name__)


class YtmusicProvider(AbstractProvider, ProviderV2):

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()
        self._user = None
        self._http_proxy = ''

    def setup_http_proxy(self, http_proxy):
        self._http_proxy = http_proxy
        self.service.setup_http_proxy(http_proxy)

    # noinspection PyPep8Naming
    class meta:
        identifier = 'ytmusic'
        name = 'YouTube Music'

    @property
    def identifier(self):
        return self.meta.identifier

    @property
    def name(self):
        return self.meta.name

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self.service.reload()
        self._user = user

    def use_model_v2(self, mtype):
        return mtype in (
            ModelType.song,
            ModelType.album,
            ModelType.artist,
            ModelType.playlist,
        )

    def library_upload_songs(self):
        songs = self.service.library_upload_songs(100)
        return [song.model() for song in songs]

    def library_upload_artists(self):
        artists = self.service.library_upload_artists(100)
        return [artist.model() for artist in artists]

    def library_upload_albums(self):
        albums = self.service.library_upload_albums(100)
        return [album.model() for album in albums]

    def library_songs(self):
        songs = self.service.library_songs(100)
        return [song.v2_model() for song in songs]

    def library_albums(self):
        albums = self.service.library_albums(100)
        return [album.v2_brief_model() for album in albums]

    def library_artists(self) -> List[BriefArtistModel]:
        artists = self.service.library_subscription_artists(100)
        return [artist.v2_brief_model() for artist in artists]

    def library_playlists(self) -> List[BriefPlaylistModel]:
        playlists = self.service.library_playlists(100)
        return [playlist.v2_brief_model() for playlist in playlists]

    def create_playlist(self, title: str, description: str, privacy_status: YtmusicPrivacyStatus,
                        video_ids: List[str] = None, source_playlist: str = None) -> bool:
        return self.service.create_playlist(title, description, privacy_status, video_ids, source_playlist)

    def playlist_info(self, identifier) -> PlaylistModel:
        return self.service.playlist_info(identifier, limit=0).v2_model()

    def add_playlist_item(self, identifier, song_id) -> bool:
        result = self.service.add_playlist_items(identifier, [song_id])
        return result.status == 'STATUS_SUCCEEDED'

    def remove_playlist_item(self, identifier, song_id, set_song_id) -> bool:
        return self.service.remove_playlist_items(identifier, [{
            'videoId': song_id,
            'setVideoId': set_song_id,
        }]) == 'STATUS_SUCCEEDED'

    def category_playlists(self, params):
        playlists = self.service.category_playlists(params)
        return [p.model() for p in playlists]

    def categories(self) -> List[Categories]:
        return self.service.categories()

    def user_from_cookie(self, cookies: dict):
        return YtBriefUserModel(
            identifier='', source=self.meta.identifier, name='Me',
            cookies=cookies)

    def has_current_user(self) -> bool:
        return self._user is not None

    def get_current_user(self):
        if not self._user:
            raise NoUserLoggedIn
        return self._user

    def user_get(self, identifier):
        if identifier is None:
            return None
        if identifier == '':
            return BriefUserModel(identifier='', source=self.meta.identifier, name='Me')
        user = self.service.user_info(identifier)
        return BriefUserModel(identifier=identifier, source=self.meta.identifier, name=user.name)

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
        return []

        id_ = song.identifier
        song_ = self.service.song_info(id_)
        return song_.list_formats() if song_ is not None else []

    def song_get_media(self, song: SongModel, quality: Quality.Audio) -> Optional[Media]:
        return None

        media = self._get_media(song, quality)
        if media is None:
            return media
        url = media.url
        # 推断(cosven): service.song_info 接口返回的 url 里面会记录请求时的 IP，
        # 如果后面真正访问 url 时，如果自己的 IP 已经变了（比如自己的代理 IP 变了），
        # 那么会碰到 403 错误。
        #
        # 注：你或许会想，把 url 中的 IP 改变当前的 public IP，是不是就行了？
        #    这其实也是不行的，因为整个 url 是已经有摘要信息的，它要和摘要匹配。
        if self.service.check_stream_url(url):
            return media
        parse_result = urlparse(url)
        kvs = parse_qs(parse_result.query)
        ips = kvs.get('ip', [])
        ip = ips[0] if ips else ''
        logger.info(
            f"url for video({song.identifier}) is invalid now, will retry! "
            f"maybe your public IP is changed (expected ip: {ip} ), (url: {url} )"
        )
        return self._get_media(song, quality)

    def _get_media(self, song, quality: Quality.Audio):
        song_info = self.service.song_info(song.identifier)
        format_code, bitrate, format_str = song_info.get_media(quality)
        url = self.service.stream_url(song_info, song.identifier, format_code)
        if url is not None:
            if 'video/mp4' in format_str:
                format_ = 'mp4'
            elif 'audio/mp4' in format_str:
                format_ = 'm4a'
            else:
                format_ = ''
            return Media(url, type_=MediaType.audio, bitrate=bitrate,
                         format=format_, http_proxy=self._http_proxy)
        return None

    def song_get_web_url(self, song) -> str:
        return f'https://music.youtube.com/watch?v={song.identifier}'

    def song_get(self, identifier):
        # ytmusicapi has not api to get song detail.
        # hack(cosven): we use get_watch_playlist to try to get song detail.
        # It works for song like '如愿-王菲'.
        result = self.service.api.get_watch_playlist(identifier)
        songs = [YtmusicWatchPlaylistSong(**track).v2_model()
                 for track in result['tracks']]
        for song in songs:
            if song.identifier == identifier:
                return song
        # I think this branch should not be reached (in most cases).
        return ModelNotFound(f'song:{identifier} not found')

    def song_list_similar(self, song):
        result = self.service.api.get_watch_playlist(song.identifier)
        songs = [YtmusicWatchPlaylistSong(**track).v2_model()
                 for track in result['tracks']
                 if track['videoId'] != song.identifier]
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
        if playlist.identifier == 'LM':
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
            albums = self.service.artist_albums(artist_info.albums.browseId,
                                                artist_info.albums.params)
        return [album.v2_brief_model() for album in albums]

    def deprecated_song_get_lyric(self, song):
        # 歌词获取报错的 workaround
        if self._app is None:
            return None
        try:
            from fuo_netease.provider import NeteaseProvider
            provider: NeteaseProvider = self._app.library.get('netease')
            if provider is None:
                return None
            result = provider.search(f'{song.title} {song.artists_name}', type_=SearchType.so)
            songs = result.songs
            if len(songs) < 1:
                return None
            return provider.song_get_lyric(songs[0])
        except ModuleNotFoundError:
            return None
        except:
            raise

    def video_list_quality(self, video) -> List[Quality.Video]:
        return []

        id_ = video.identifier
        song_ = self.service.song_info(id_)
        return song_.list_video_formats() if song_ is not None else []

    def video_get(self, identifier):
        song = self.song_get(identifier)
        return VideoModel(identifier=song.identifier, source=song.source, title=song.title,
                          artists=song.artists, duration=song.duration, cover=song.pic_url)

    def video_get_media(self, video, quality) -> Optional[Media]:
        return None

        song_info = self.service.song_info(video.identifier)
        format_code = song_info.get_mv(quality)
        audio_formats = song_info.list_formats()
        audio_code, _, __ = song_info.get_media(audio_formats[0])
        url = self.service.stream_url(song_info, video.identifier, format_code)
        audio_url = self.service.stream_url(song_info, video.identifier, audio_code)
        if url is None or audio_url is None:
            return None
        return Media(VideoAudioManifest(url, audio_url), http_proxy=self._http_proxy)

    def song_get_mv(self, song: BriefSongProtocol) -> BriefVideoModel:
        return BriefVideoModel(identifier=song.identifier, source=song.source, title=song.title,
                               artists_name=song.artists_name, duration_ms=song.duration_ms)

    def upload_song(self, path: str) -> bool:
        return self.service.upload_song(path) == 'STATUS_SUCCEEDED'

    def delete_uploaded_song(self, entity_id: str) -> bool:
        return self.service.delete_upload_song(entity_id) == 'STATUS_SUCCEEDED'


provider = YtmusicProvider()
