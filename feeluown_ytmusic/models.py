from typing import Optional, Union, List
from pydantic import BaseModel as PydanticBaseModel
# noinspection PyProtectedMember
from pydantic.fields import Field
from pydantic.main import ModelMetaclass


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
    pass


class SearchNestedArtist(BaseModel):
    id: str
    name: str


class SearchNestedThumbnail(BaseModel):
    url: str  # 图片地址
    width: int
    height: int


class YtmusicSearchBase(BaseModel):
    category: str
    resultType: str


class YtmusicSearchSong(YtmusicSearchBase):
    class Album(BaseModel):
        id: str
        name: str

    title: str  # 歌名
    album: Album  # 专辑信息
    feedbackTokens: dict
    videoId: str  # 歌曲ID
    duration: str  # 歌曲时长 eg.3:50
    artists: List[SearchNestedArtist]  # 歌手信息
    isAvailable: bool
    isExplicit: bool
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicLibrarySong(YtmusicSearchSong):
    likeStatus: str  # LIKE


class YtmusicSearchAlbum(YtmusicSearchBase):
    title: str  # 专辑名
    type: str  # 专辑类型
    year: int  # 年
    artists: List[SearchNestedArtist]  # 歌手信息
    browseId: str  # 查询ID
    isExplicit: bool
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchArtist(YtmusicSearchBase):
    artist: str  # 歌手名
    shuffleId: str
    radioId: str
    browseId: str  # 查询ID
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicLibraryArtist(YtmusicSearchArtist):
    subscribers: str  # 歌曲数量


class YtmusicSearchPlaylist(YtmusicSearchBase):
    title: str  # 歌单名
    itemCount: int  # 歌曲数量
    author: str  # 歌单作者
    browseId: str  # 查询ID
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchVideo(YtmusicSearchBase):
    title: str  # 视频标题
    views: str  # 播放量 eg:13K
    videoId: str  # 视频ID
    duration: str  # 视频时长 eg.3:50
    artists: List[SearchNestedArtist]  # 歌手信息
    thumbnails: List[SearchNestedThumbnail]  # 封面信息
    playlistId: str


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


class AlbumInfo(BaseModel):
    title: str  # 专辑名
    type: str
    thumbnails: List[SearchNestedThumbnail]  # 封面信息
    artists: List[SearchNestedArtist]  # 歌手信息
    year: str
    trackCount: int
    duration: str  # eg.5 minutes, 14 seconds
    audioPlaylistId: str
    tracks: List[YtmusicSearchSong]  # 专辑歌曲


class SongInfo(BaseModel):
    class VideoDetails(BaseModel):
        class Thumbnails(BaseModel):
            thumbnails: List[SearchNestedThumbnail]

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

        expiresInSeconds: int
        formats: List[Format]
        adaptiveFormats: List[Format]

    videoDetails: VideoDetails
    streamingData: StreamingData


class PlaylistNestedResult(BaseModel):
    title: str
    playlistId: str
    thumbnails: List[SearchNestedThumbnail]


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
