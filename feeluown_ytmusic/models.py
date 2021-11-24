from typing import Optional, Union, List
from pydantic import BaseModel as PydanticBaseModel
# noinspection PyProtectedMember
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


class YtmusicSearchSong(BaseModel):
    class Album(BaseModel):
        id: str
        name: str

    category: str
    resultType: str
    title: str  # 歌名
    album: Album  # 专辑信息
    feedbackTokens: dict
    videoId: str  # 歌曲ID
    duration: str  # 歌曲时长 eg.3:50
    artists: List[SearchNestedArtist]  # 歌手信息
    isExplicit: bool
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchAlbum(BaseModel):
    category: str
    resultType: str
    title: str  # 专辑名
    type: str  # 专辑类型
    year: int  # 年
    artists: List[SearchNestedArtist]  # 歌手信息
    browseId: str  # 查询ID
    isExplicit: bool
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchArtist(BaseModel):
    category: str
    resultType: str
    artist: str  # 歌手名
    shuffleId: str
    radioId: str
    browseId: str  # 查询ID
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchPlaylist(BaseModel):
    category: str
    resultType: str
    title: str  # 歌单名
    itemCount: int  # 歌曲数量
    author: str  # 歌单作者
    browseId: str  # 查询ID
    thumbnails: List[SearchNestedThumbnail]  # 封面信息


class YtmusicSearchVideo(BaseModel):
    category: str
    resultType: str
    title: str  # 视频标题
    views: str  # 播放量 eg:13K
    videoId: str  # 视频ID
    duration: str  # 视频时长 eg.3:50
    artists: List[SearchNestedArtist]  # 歌手信息
    thumbnails: List[SearchNestedThumbnail]  # 封面信息
