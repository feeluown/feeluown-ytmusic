from typing import List, Optional

from feeluown.library import AbstractProvider, ProviderV2, ModelType, ProviderFlags as Pf, SongProtocol, ModelState, \
    SongModel
from feeluown.media import Quality, Media
from feeluown.models import SearchType, SearchModel

from fuo_ytmusic.service import YtmusicService, YtmusicType


class YtmusicProvider(AbstractProvider, ProviderV2):
    service: YtmusicService

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()

    class meta:
        identifier = 'ytmusic'
        name = 'Youtube Music'
        flags = {
            ModelType.song: (Pf.model_v2 | Pf.multi_quality | Pf.mv),
            ModelType.video: (Pf.multi_quality),
        }

    @property
    def identifier(self):
        return self.meta.identifier

    @property
    def name(self):
        return self.meta.name

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
        format_code = song_info.get_media(quality)
        url = self.service.stream_url(song.identifier, format_code)
        print(url)
        return Media(url) if url is not None else None

    def song_get_lyric(self, song):
        return None
