from typing import List

from feeluown.library import AbstractProvider, ProviderV2, ModelType, ProviderFlags as Pf, SongProtocol, ModelState
from feeluown.media import Quality
from feeluown.models import SearchType, SearchModel

from feeluown_ytmusic.service import YtmusicService, YtmusicType


class YtmusicProvider(AbstractProvider, ProviderV2):
    service: YtmusicService

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()

    class Meta:
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
        setattr(model, ytmusic_type.value, [])
        return model

    def song_list_quality(self, song) -> List[Quality.Audio]:
        id_ = song.identifier
        song_ = self.service.song_info(id_)
        return song_.list_formats() if song_ is not None else []
