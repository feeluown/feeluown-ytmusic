from typing import List

from feeluown.library import AbstractProvider, ProviderV2, ModelType, ProviderFlags as Pf, SongProtocol
from feeluown.media import Quality

from feeluown_ytmusic.service import YtmusicService


class YtmusicProvider(AbstractProvider, ProviderV2):
    service: YtmusicService

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()

    class Meta:
        identifier = 'ytmusic'
        name = 'Youtube Music'
        flags = {
            ModelType.song: (Pf.model_v2, Pf.get, Pf.multi_quality)
        }

    @property
    def identifier(self):
        return self.meta.identifier

    @property
    def name(self):
        return self.meta.name

    def search(self, *args, **kwargs):
        pass

    def song_get(self, identifier) -> SongProtocol:
        pass

    def song_list_quality(self, song) -> List[Quality.Audio]:
        pass
