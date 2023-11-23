from typing import Optional, Union, List, Tuple

# noinspection PyProtectedMember
from pydantic.v1.fields import Field
from pydantic.v1 import BaseModel as PydanticBaseModel
from pydantic.v1.main import ModelMetaclass

from feeluown.utils.reader import SequentialReader
from feeluown.media import Quality
from feeluown.library import (
    VideoModel, ModelState, BriefArtistModel, BriefUserModel,
    AlbumModel as AlbumModelV2, BriefSongModel, SongModel as SongModelV2,
    BriefAlbumModel, ArtistModel as ArtistModelV2, PlaylistModel,
    BriefPlaylistModel,
)
from feeluown.library import AlbumType

from fuo_ytmusic.timeparse import timeparse


class AllowOptional(ModelMetaclass):
    def __new__(mcs, name, bases, namespaces, **kwargs):
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            if hasattr(base, '__annotations__'):
                annotations = {**annotations, **base.__annotations__}
        for field in annotations:
            if not field.startswith('__'):
                if hasattr(annotations[field], '__origin__') and annotations[field].__origin__ is Union:
                    continue
                annotations[field] = Optional[annotations[field]]
        namespaces['__annotations__'] = annotations
        return super().__new__(mcs, name, bases, namespaces, **kwargs)


class BaseModel(PydanticBaseModel, metaclass=AllowOptional):
    @property
    def source(self):
        return 'ytmusic'


class SearchNestedArtist(BaseModel):
    id: str
    name: str

    def v2_brief_model(self) -> BriefArtistModel:
        return BriefArtistModel(identifier=self.id or '', source=self.source, name=self.name or '')


class YtmusicArtistsMixin:
    artists: List[SearchNestedArtist]  # 歌手信息

    def v2_brief_artist_models(self) -> List[BriefArtistModel]:
        return [artist.v2_brief_model() for artist in (self.artists or [])
                if artist.id is not None]

    @property
    def artists_name(self):
        if self.artists is None:
            return ''
        return ' / '.join([a.name for a in self.artists])


class SearchNestedThumbnail(BaseModel):
    url: str  # 图片地址
    width: int
    height: int


class YtmusicCoverMixin:
    thumbnails: List[SearchNestedThumbnail]  # 封面信息

    @property
    def cover(self) -> Optional[str]:
        if self.thumbnails is not None and len(self.thumbnails) > 0:
            return self.thumbnails[-1].url
        return None

    @property
    def thumbnail(self) -> Optional[str]:
        if self.thumbnails is not None and len(self.thumbnails) > 0:
            return self.thumbnails[0].url
        return None


class YtmusicDurationMixin:
    duration: str  # 歌曲时长 eg.3:50

    @property
    def duration_ms(self) -> int:
        if self.duration is None:
            return 0
        return int(timeparse(self.duration) * 1000)


class YtmusicAlbumSong(BaseModel, YtmusicArtistsMixin, YtmusicDurationMixin):
    title: str
    album: str
    videoId: str

    def v2_brief_model(self) -> BriefSongModel:
        return BriefSongModel(
            identifier=self.videoId,
            source=self.source,
            title=self.title,
            artists_name=self.artists_name,
            album_name=self.album,
            duration_ms=self.duration
        )

    def v2_model_with_brief_album(self, album: BriefAlbumModel) -> SongModelV2:
        return SongModelV2(
            identifier=self.videoId,
            source=self.source,
            title=self.title,
            album=album,
            artists=self.v2_brief_artist_models(),
            duration=self.duration_ms,
        )


class YtmusicSearchBase(BaseModel):
    category: str
    resultType: str


class YtmusicSearchSong(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin, YtmusicDurationMixin):
    class Album(BaseModel):
        id: str
        name: str

        def model(self) -> BriefAlbumModel:
            album = BriefAlbumModel(identifier=self.id or '', source=self.source, name=self.name)
            if self.id is None:
                album.state = ModelState.not_exists
            return album

    title: str  # 歌名
    album: Album  # 专辑信息
    feedbackTokens: dict
    videoId: str  # 歌曲ID
    isAvailable: bool
    isExplicit: bool

    def v2_brief_model(self) -> BriefSongModel:
        song = BriefSongModel(
            identifier=self.videoId or '',
            source=self.source,
            title=self.title,
            artists_name=self.artists_name,
            album_name=self.album.name if self.album else '',
            duration_ms=self.duration
        )
        if not song.identifier:
            song.state = ModelState.not_exists
        return song

    def v2_model(self) -> SongModelV2:
        if self.album:
            album = self.album.model()
        else:
            album = None
        song = SongModelV2(
            identifier=self.videoId or '',
            source=self.source,
            title=self.title,
            artists=self.v2_brief_artist_models(),
            album=album,
            duration=self.duration_ms,
            pic_url=self.cover or '',
        )
        if not song.identifier:
            song.state = ModelState.not_exists
        return song


class YtmusicWatchPlaylistSong(YtmusicSearchSong):
    year: str  # This field exists in get_watch_playlist API.

    def v2_model(self) -> SongModelV2:
        song = super().v2_model()
        song.date = self.year or ''
        return song


class YtmusicLibrarySong(YtmusicSearchSong):
    likeStatus: str  # LIKE
    setVideoId: str
    entityId: str


class YtmusicHistorySong(YtmusicLibrarySong):
    played: str  # 上次播放 eg November 2021


class YtmusicSearchAlbum(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin):
    title: str  # 专辑名
    type: str  # 专辑类型
    year: Optional[Union[int, str]]  # 年
    browseId: str  # 查询ID
    isExplicit: bool

    @property
    def album_type(self) -> AlbumType:
        if self.type == 'Single':
            return AlbumType.single
        return AlbumType.standard

    def v2_brief_model(self) -> BriefAlbumModel:
        return BriefAlbumModel(
            identifier=self.browseId,
            source=self.source,
            name=self.title,
            artists_name=self.artists_name,
        )


class YtmusicSearchArtist(YtmusicSearchBase, YtmusicCoverMixin):
    artist: str  # 歌手名
    shuffleId: str
    radioId: str
    browseId: str  # 查询ID

    def v2_brief_model(self) -> BriefArtistModel:
        return BriefArtistModel(identifier=self.browseId, source=self.source, name=self.artist)


class YtmusicLibraryArtist(YtmusicSearchArtist):
    subscribers: str  # 歌曲数量


class YtmusicSearchPlaylist(YtmusicSearchBase, YtmusicCoverMixin):
    title: str  # 歌单名
    itemCount: Optional[int] = None  # 歌曲数量
    author: str  # 歌单作者
    browseId: str  # 查询ID

    def v2_brief_model(self) -> BriefPlaylistModel:
        return BriefPlaylistModel(
            identifier=self.browseId,
            source=self.source,
            name=self.title,
            creator_name=self.author or '',
        )


class YtmusicSearchVideo(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin, YtmusicDurationMixin):
    title: str  # 视频标题
    views: str  # 播放量 eg:13K
    videoId: str  # 视频ID
    playlistId: str

    def v2_model(self) -> VideoModel:
        return VideoModel(
            identifier=self.videoId,
            source=self.source,
            title=self.title,
            cover=self.cover,
            artists=self.v2_brief_artist_models(),
            duration=self.duration_ms
        )


class YtmusicDispatcher:
    RESULT_TYPE_MAP = {
        'video': YtmusicSearchVideo,
        'song': YtmusicSearchSong,
        'artist': YtmusicSearchArtist,
        'album': YtmusicSearchAlbum,
        'playlist': YtmusicSearchPlaylist,
    }

    @classmethod
    def search_result_dispatcher(cls, **data) \
            -> Union[YtmusicSearchBase, YtmusicSearchVideo, YtmusicSearchSong, YtmusicSearchArtist, YtmusicSearchAlbum,
                     YtmusicSearchPlaylist]:
        clazz = cls.RESULT_TYPE_MAP.get(data.get('resultType') or '')
        return clazz(**data) if clazz is not None else YtmusicSearchBase(**data)


class ArtistInfo(BaseModel):
    class Songs(BaseModel):
        browseId: str  # 查询ID
        results: List[YtmusicSearchSong]  # 歌曲列表（部分）

    class Albums(BaseModel):
        browseId: str  # 查询ID
        results: List[YtmusicSearchAlbum]  # 专辑列表（部分）
        params: str  # 不知道是啥

    class Videos(BaseModel):
        browseId: str  # 查询ID
        results: List[YtmusicSearchVideo]  # 视频列表（部分）

    class RelatedArtists(BaseModel):
        results: List[YtmusicSearchArtist]  # 相关歌手

    name: str  # 歌手名
    description: str  # 描述
    views: str  # 播放量 eg.177,865,792 views
    channelId: str
    shuffleId: str
    radioId: str
    subscribers: str  # 订阅量 eg.230K
    subscribed: bool  # 是否已订阅
    thumbnails: List[SearchNestedThumbnail]  # 封面信息
    songs: Songs
    albums: Albums  # 专辑
    singles: Albums  # 单曲专辑
    videos: Videos
    related: RelatedArtists

    def v2_model(self, identifier) -> ArtistModelV2:
        # Note that the channelId is different from the identifier.
        # Though the channelId also refers to the artist,
        # it's songs is a empty list.
        return ArtistModelV2(
            identifier=identifier,
            source=self.source,
            name=self.name,
            pic_url=(self.thumbnails[0].url if self.thumbnails else ''),
            aliases=[],
            hot_songs=[],
            description=self.description or '',
        )


class AlbumInfo(BaseModel, YtmusicArtistsMixin, YtmusicCoverMixin):
    title: str  # 专辑名
    type: str
    year: str
    trackCount: int
    duration: str  # eg.5 minutes, 14 seconds
    audioPlaylistId: str
    tracks: List[YtmusicAlbumSong]  # 专辑歌曲
    # ytmusicapi.get_album has this field. Not sure if other api has this field.
    description: str = ''

    def v2_model_with_identifier(self, identifier) -> AlbumModelV2:
        brief_album = BriefAlbumModel(
            identifier=identifier,
            source=self.source,
            name=self.title,
            artists_name=self.artists_name,
        )
        return AlbumModelV2(
            identifier=identifier,
            source=self.source,
            name=self.title,
            cover=self.cover,
            songs=[t.v2_model_with_brief_album(brief_album) for t in self.tracks],
            artists=self.v2_brief_artist_models(),
            description=self.description,
            released=self.year,
        )


class SongInfo(BaseModel):
    class VideoDetails(BaseModel):
        class Thumbnails(BaseModel, YtmusicCoverMixin):
            pass

        videoId: str
        title: str
        lengthSeconds: int
        channelId: str
        isOwnerViewing: bool
        isCrawlable: bool
        thumbnail: Thumbnails
        averageRating: float
        allowRatings: bool
        viewCount: int
        author: str
        isPrivate: bool
        musicVideoType: str
        isLiveContent: bool

    class StreamingData(BaseModel):
        class Format(BaseModel):
            itag: int
            url: str
            mimeType: str
            bitrate: int
            initRange: dict
            indexRange: dict
            lastModified: str
            contentLength: int
            audioQuality: str  # AUDIO_QUALITY_LOW AUDIO_QUALITY_MEDIUM
            audioSampleRate: int  # 48000
            quality: str
            signatureCipher: str

        expiresInSeconds: int
        formats: List[Format]
        adaptiveFormats: List[Format]

    videoDetails: VideoDetails
    streamingData: StreamingData

    def list_formats(self) -> List[Quality.Audio]:
        qualities = set()
        if self.streamingData is None:
            return []
        for format_ in self.streamingData.adaptiveFormats:
            if format_.audioQuality is None:
                continue
            if format_.audioQuality == 'AUDIO_QUALITY_LOW':
                qualities.add(Quality.Audio.lq)
            elif format_.audioQuality == 'AUDIO_QUALITY_MEDIUM':
                qualities.add(Quality.Audio.sq)
            elif format_.audioQuality == 'AUDIO_QUALITY_HIGH':
                qualities.add(Quality.Audio.hq)
        return list(qualities)

    def list_video_formats(self) -> List[Quality.Video]:
        qualities = set()
        for format_ in self.streamingData.adaptiveFormats:
            if format_.audioQuality is not None:
                continue
            if format_.quality == 'hd1080':
                qualities.add(Quality.Video.fhd)
            if format_.quality == 'hd720':
                qualities.add(Quality.Video.hd)
            if format_.quality == 'large':
                qualities.add(Quality.Video.sd)
            if format_.quality == 'medium':
                qualities.add(Quality.Video.ld)
        return list(qualities)

    def get_media(self, quality: Quality.Audio) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        for format_ in self.streamingData.adaptiveFormats:
            if format_.audioQuality is None:
                continue
            if quality in (Quality.Audio.hq, Quality.Audio.shq) and format_.audioQuality == 'AUDIO_QUALITY_HIGH':
                return format_.itag, int(format_.bitrate / 1024), format_.mimeType
            if quality == Quality.Audio.sq and format_.audioQuality == 'AUDIO_QUALITY_MEDIUM':
                return format_.itag, int(format_.bitrate / 1024), format_.mimeType
            if quality == Quality.Audio.lq and format_.audioQuality == 'AUDIO_QUALITY_LOW':
                return format_.itag, int(format_.bitrate / 1024), format_.mimeType
        return None, None, None

    def get_mv(self, quality) -> Optional[int]:
        for format_ in self.streamingData.adaptiveFormats:
            if format_.audioQuality is not None:
                continue
            if quality == Quality.Video.fhd and format_.quality == 'hd1080':
                return format_.itag
            if quality == Quality.Video.hd and format_.quality == 'hd720':
                return format_.itag
            if quality == Quality.Video.sd and format_.quality == 'large':
                return format_.itag
            if quality == Quality.Video.ld and format_.quality == 'medium':
                return format_.itag
        return None


class PlaylistNestedResult(BaseModel, YtmusicCoverMixin):
    title: str
    playlistId: str

    def v2_brief_model(self) -> BriefPlaylistModel:
        return BriefPlaylistModel(
            identifier=self.playlistId,
            source=self.source,
            name=self.title,
            creator_name='',
        )


class UserInfo(BaseModel):
    class Playlists(BaseModel):
        browseId: str
        results: List[PlaylistNestedResult]
        params: str

    class Videos(BaseModel):
        browseId: str  # 查询ID
        results: List[YtmusicSearchVideo]  # 视频列表（部分）

    name: str
    playlists: Playlists
    videos: Videos


class Categories(BaseModel):
    class Category(BaseModel):
        title: str
        params: str

    key: str
    value: List[Category]


class TopCharts(BaseModel):
    class Countries(BaseModel):
        class Selected(BaseModel):
            text: str

        selected: Selected
        options: List[str]

    class Videos(BaseModel):
        playlist: str  # PlaylistID
        items: List[YtmusicSearchVideo]  # 视频列表（部分）

    class Artists(BaseModel):
        items: List[YtmusicSearchArtist]  # 歌手列表

    countries: Countries
    videos: Videos
    artists: Artists


class PlaylistInfo(BaseModel, YtmusicCoverMixin):
    class Author(BaseModel):
        id: str
        name: str

    id: str
    privacy: str  # PUBLIC
    title: str  # 歌单名
    description: Optional[str]
    author: Author
    year: int
    duration: str
    trackCount: int
    tracks: List[YtmusicLibrarySong]
    fetched_tracks: set = Field(default_factory=set)

    def v2_model(self):
        creator = None
        if self.author is not None and self.author.id is not None:
            creator = BriefUserModel(
                identifier=self.author.id,
                source=self.source,
                name=self.author.name or '',
            )
        return PlaylistModel(
            identifier=self.id,
            source=self.source,
            name=self.title,
            cover=self.cover,
            description=self.description or '',
            creator=creator
        )

    def reader(self, provider) -> SequentialReader:
        total_count = self.trackCount
        self.fetched_tracks = set()

        def g():
            counter = 0
            offset = 0
            per = 50
            while offset < total_count:
                end = min(offset + per, total_count)
                data: PlaylistInfo = provider.service.playlist_info(self.id, limit=end)
                tracks_data = data.tracks
                for track_data in tracks_data:
                    if track_data.videoId is not None and track_data.videoId in self.fetched_tracks:
                        continue
                    self.fetched_tracks.add(track_data.videoId)
                    counter += 1
                    yield track_data.v2_brief_model()
                if counter >= total_count:
                    break
                offset += per
            self.fetched_tracks.clear()

        return SequentialReader(g(), total_count)


class PlaylistAddItemResponse(BaseModel):
    class PlaylistEditResult(BaseModel):
        videoId: str
        setVideoId: str

    status: str  # STATUS_SUCCEEDED STATUS_FAILED
    playlistEditResults: List[PlaylistEditResult]


# FeelUOwn models

class YtmusicSongModel(SongModelV2):
    setVideoId: Optional[str]
    entityId: Optional[str]


class YtBriefUserModel(BriefUserModel):
    cookies: dict = {}
