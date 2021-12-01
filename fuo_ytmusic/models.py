from typing import Optional, Union, List
from pydantic import BaseModel as PydanticBaseModel
# noinspection PyProtectedMember
from pydantic.fields import Field
from pydantic.main import ModelMetaclass

from feeluown.media import Quality, Media
from feeluown.library import SongModel, BriefArtistModel, BriefAlbumModel, VideoModel
from feeluown.models import AlbumModel, AlbumType, ArtistModel, PlaylistModel

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

    def model(self) -> BriefArtistModel:
        return BriefArtistModel(identifier=self.id or '', source=self.source, name=self.name)


class YtmusicArtistsMixin:
    artists: List[SearchNestedArtist]  # 歌手信息

    @property
    def artists_model(self) -> Optional[List[BriefArtistModel]]:
        if self.artists is not None:
            return [artist.model() for artist in self.artists]
        return None


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


class YtmusicDurationMixin:
    duration: str  # 歌曲时长 eg.3:50

    @property
    def duration_ms(self) -> int:
        return int(timeparse(self.duration) * 1000)


class YtmusicSearchBase(BaseModel):
    category: str
    resultType: str


class YtmusicSearchSong(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin, YtmusicDurationMixin):
    class Album(BaseModel):
        id: str
        name: str

        def model(self) -> BriefAlbumModel:
            return BriefAlbumModel(identifier=self.id, source=self.source, name=self.name)

    title: str  # 歌名
    album: Album  # 专辑信息
    feedbackTokens: dict
    videoId: str  # 歌曲ID
    isAvailable: bool
    isExplicit: bool

    def model(self) -> SongModel:
        song = SongModel(identifier=self.videoId, source=self.source, title=self.title, artists=self.artists_model,
                         duration=self.duration_ms)
        if self.album is not None:
            song.album = self.album.model()
        return song


class YtmusicLibrarySong(YtmusicSearchSong):
    likeStatus: str  # LIKE


class YtmusicHistorySong(YtmusicLibrarySong):
    played: str  # 上次播放 eg November 2021


class YtmusicSearchAlbum(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin):
    title: str  # 专辑名
    type: str  # 专辑类型
    year: int  # 年
    browseId: str  # 查询ID
    isExplicit: bool

    @property
    def album_type(self) -> AlbumType:
        if self.type == 'Single':
            return AlbumType.single
        return AlbumType.standard

    def model(self) -> AlbumModel:
        return AlbumModel(identifier=self.browseId, source=self.source, name=self.title, type=self.album_type,
                          cover=self.cover, artists=self.artists_model)


class YtmusicSearchArtist(YtmusicSearchBase, YtmusicCoverMixin):
    artist: str  # 歌手名
    shuffleId: str
    radioId: str
    browseId: str  # 查询ID

    def model(self) -> ArtistModel:
        return ArtistModel(identifier=self.browseId, source=self.source, name=self.artist, cover=self.cover)


class YtmusicLibraryArtist(YtmusicSearchArtist):
    subscribers: str  # 歌曲数量


class YtmusicSearchPlaylist(YtmusicSearchBase, YtmusicCoverMixin):
    title: str  # 歌单名
    itemCount: int  # 歌曲数量
    author: str  # 歌单作者
    browseId: str  # 查询ID

    def model(self) -> PlaylistModel:
        return PlaylistModel(identifier=self.browseId, source=self.source, name=self.title, cover=self.cover)


class YtmusicSearchVideo(YtmusicSearchBase, YtmusicCoverMixin, YtmusicArtistsMixin, YtmusicDurationMixin):
    title: str  # 视频标题
    views: str  # 播放量 eg:13K
    videoId: str  # 视频ID
    playlistId: str

    def model(self) -> VideoModel:
        return VideoModel(identifier=self.videoId, source=self.source, title=self.title, cover=self.cover,
                          artists=self.artists_model, duration=self.duration_ms)


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
        clazz = cls.RESULT_TYPE_MAP.get(data.get('resultType'))
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


class AlbumInfo(BaseModel, YtmusicArtistsMixin, YtmusicCoverMixin):
    title: str  # 专辑名
    type: str
    year: str
    trackCount: int
    duration: str  # eg.5 minutes, 14 seconds
    audioPlaylistId: str
    tracks: List[YtmusicSearchSong]  # 专辑歌曲


class SongInfo(BaseModel):
    class VideoDetails(BaseModel):
        class Thumbnails(BaseModel, YtmusicCoverMixin):
            pass

        videoId: str
        title: str
        lengthSeconds: int
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

        expiresInSeconds: int
        formats: List[Format]
        adaptiveFormats: List[Format]

    videoDetails: VideoDetails
    streamingData: StreamingData

    def list_formats(self) -> List[Quality.Audio]:
        qualities = set()
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

    def get_media(self, quality: Quality.Audio) -> Optional[int]:
        for format_ in self.streamingData.adaptiveFormats:
            if format_.audioQuality is None:
                continue
            if quality in (Quality.Audio.hq, Quality.Audio.shq) and format_.audioQuality == 'AUDIO_QUALITY_HIGH':
                return format_.itag
            if quality == Quality.Audio.sq and format_.audioQuality == 'AUDIO_QUALITY_MEDIUM':
                return format_.itag
            if quality == Quality.Audio.lq and format_.audioQuality == 'AUDIO_QUALITY_LOW':
                return format_.itag
        return None


class PlaylistNestedResult(BaseModel, YtmusicCoverMixin):
    title: str
    playlistId: str


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

    forYou: List[Category] = Field(alias="For you")
    moods: List[Category] = Field(alias="Moods & moments")
    genres: List[Category] = Field(alias="Genres")


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
    description: str
    author: Author
    year: int
    duration: str
    trackCount: int
    tracks: List[YtmusicLibrarySong]
