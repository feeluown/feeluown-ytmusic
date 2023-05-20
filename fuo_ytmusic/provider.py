from typing import List, Optional

from feeluown.excs import NoUserLoggedIn
from feeluown.library import AbstractProvider, ProviderV2, ModelType, ProviderFlags as Pf, SongModel, BriefVideoModel, \
    BriefUserModel, ModelType
from feeluown.media import Quality, Media, VideoAudioManifest, MediaType
from feeluown.models import SearchType, SearchModel
from feeluown.library.model_protocol import BriefSongProtocol
from fuo_netease.models import NSearchModel
from fuo_netease.provider import NeteaseProvider

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.models import (
    YtmusicPlaylistModel, Categories, YtBriefUserModel,
)
from fuo_ytmusic.service import YtmusicService, YtmusicType, YtmusicPrivacyStatus


class YtmusicProvider(AbstractProvider, ProviderV2):
    service: YtmusicService

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()
        self._user = None
        YtmusicPlaylistModel.provider = self

    def initialize(self, app):
        self._app = app

    # noinspection PyPep8Naming
    class meta:
        identifier = 'ytmusic'
        name = 'YouTube Music'
        flags = {
            ModelType.song: (Pf.model_v2 | Pf.multi_quality | Pf.mv | Pf.lyric),
            ModelType.video: Pf.multi_quality,
            ModelType.album: Pf.get,
            ModelType.artist: Pf.get,
        }

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
        self._user = user

    def use_model_v2(self, mtype):
        return mtype in (ModelType.album, ModelType.artist)

    def library_songs(self):
        songs = self.service.library_songs(100)
        return [song.model() for song in songs]

    def library_upload_songs(self):
        songs = self.service.library_upload_songs(100)
        return [song.model() for song in songs]

    def library_upload_artists(self):
        artists = self.service.library_upload_artists(100)
        return [artist.model() for artist in artists]

    def library_upload_albums(self):
        albums = self.service.library_upload_albums(100)
        return [album.model() for album in albums]

    def library_albums(self):
        albums = self.service.library_albums(100)
        return [album.model() for album in albums]

    def library_artists(self):
        raise
        artists = self.service.library_subscription_artists(100)
        return [artist.model() for artist in artists]

    def library_playlists(self) -> List[YtmusicPlaylistModel]:
        playlists = self.service.library_playlists(100)
        return [playlist.model() for playlist in playlists]

    def create_playlist(self, title: str, description: str, privacy_status: YtmusicPrivacyStatus,
                        video_ids: List[str] = None, source_playlist: str = None) -> bool:
        return self.service.create_playlist(title, description, privacy_status, video_ids, source_playlist)

    def playlist_info(self, identifier) -> YtmusicPlaylistModel:
        return self.service.playlist_info(identifier, limit=0).model()

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
        return HEADER_FILE.exists()

    def get_current_user(self):
        if not HEADER_FILE.exists():
            raise NoUserLoggedIn
        return BriefUserModel(identifier='', source=self.meta.identifier, name='Me')

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
        model = SearchModel(q=keyword)
        setattr(model, ytmusic_type.value, [r.model() for r in results])
        return model

    def song_list_quality(self, song) -> List[Quality.Audio]:
        id_ = song.identifier
        song_ = self.service.song_info(id_)
        return song_.list_formats() if song_ is not None else []

    def song_get_media(self, song: SongModel, quality: Quality.Audio) -> Optional[Media]:
        song_info = self.service.song_info(song.identifier)
        format_code, bitrate, format_str = song_info.get_media(quality)
        url = self.service.stream_url(song.identifier, format_code)
        if url is not None:
            return Media(url, type_=MediaType.audio, bitrate=bitrate,
                         format=format_str, http_proxy='http://127.0.0.1:7890')
        return

    def album_get(self, identifier):
        album_info = self.service.album_info(identifier)
        return album_info.v2_model_with_identifier(identifier)

    def artist_get(self, identifier):
        return self.service.artist_info(identifier).v2_model()

    def artist_create_songs_rd(self, artist):
        artist_info = self.service.artist_info(artist.identifier)
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
        provider: NeteaseProvider = self._app.library.get('netease')
        if provider is None:
            return None
        result: NSearchModel = provider.search(f'{song.title} {song.artists_name}', type_=SearchType.so)
        songs = result.songs
        if len(songs) < 1:
            return None
        return provider.song_get_lyric(songs[0])

    def video_list_quality(self, video) -> List[Quality.Video]:
        id_ = video.identifier
        song_ = self.service.song_info(id_)
        return song_.list_video_formats() if song_ is not None else []

    def video_get_media(self, video, quality) -> Optional[Media]:
        song_info = self.service.song_info(video.identifier)
        format_code = song_info.get_mv(quality)
        audio_formats = song_info.list_formats()
        audio_code, _, __ = song_info.get_media(audio_formats[0])
        url = self.service.stream_url(video.identifier, format_code)
        audio_url = self.service.stream_url(video.identifier, audio_code)
        if url is None or audio_url is None:
            return None
        url = url.replace('https://', 'http://')
        audio_url = audio_url.replace('https://', 'http://')
        return Media(VideoAudioManifest(url, audio_url))

    def song_get_mv(self, song: BriefSongProtocol) -> BriefVideoModel:
        return BriefVideoModel(identifier=song.identifier, source=song.source, title=song.title,
                               artists_name=song.artists_name, duration_ms=song.duration_ms)

    def upload_song(self, path: str) -> bool:
        return self.service.upload_song(path) == 'STATUS_SUCCEEDED'

    def delete_uploaded_song(self, entity_id: str) -> bool:
        return self.service.delete_upload_song(entity_id) == 'STATUS_SUCCEEDED'


provider = YtmusicProvider()
