import copy
from types import SimpleNamespace

import pytest
from feeluown.excs import ProviderIOError
from feeluown.media import Quality
from yt_dlp import DownloadError

from fuo_ytmusic import provider as provider_module
from fuo_ytmusic.provider import YtmusicProvider


class _ApiStub:
    def __init__(self, user_agent=""):
        self._user_agent = user_agent

    def get_user_agent(self):
        return self._user_agent


class _ServiceStub:
    def __init__(self, api, cookiefile=""):
        self.api = api
        self.cookiefile = cookiefile

    def get_user_agent(self):
        return self.api.get_user_agent()

    def get_ytdlp_cookiefile_path(self):
        return self.cookiefile


class _YtdlpCapture:
    last_opts = None

    def __init__(self, opts):
        self.__class__.last_opts = copy.deepcopy(opts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, _url, download=False):
        assert download is False
        return {
            "url": "https://cdn.example.com/audio.m4a",
            "ext": "m4a",
            "abr": 128,
        }


class _YtdlpFailure:
    def __init__(self, _opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, _url, download=False):
        assert download is False
        raise DownloadError("bot check", None)


def test_song_get_media_passes_cookiefile_and_user_agent_to_ytdlp(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(
        _ApiStub(user_agent="ytmusic-agent"),
        cookiefile="/tmp/ytmusic.cookies.txt",
    )
    monkeypatch.setattr(provider_module, "YoutubeDL", _YtdlpCapture)

    media = provider.song_get_media(
        SimpleNamespace(identifier="video-id"), Quality.Audio.sq
    )

    assert media.url == "https://cdn.example.com/audio.m4a"
    assert media.props.format == "m4a"
    assert media.props.bitrate == 128
    assert _YtdlpCapture.last_opts["cookiefile"] == "/tmp/ytmusic.cookies.txt"
    assert _YtdlpCapture.last_opts["user_agent"] == "ytmusic-agent"


def test_song_get_media_skips_cookiefile_when_unavailable(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub())
    monkeypatch.setattr(provider_module, "YoutubeDL", _YtdlpCapture)

    provider.song_get_media(SimpleNamespace(identifier="video-id"), Quality.Audio.sq)

    assert "cookiefile" not in _YtdlpCapture.last_opts
    assert "user_agent" not in _YtdlpCapture.last_opts


def test_song_get_media_raises_user_actionable_error(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub(), cookiefile="/tmp/ytmusic.cookies.txt")
    monkeypatch.setattr(provider_module, "YoutubeDL", _YtdlpFailure)

    with pytest.raises(ProviderIOError, match="cookies may be expired"):
        provider.song_get_media(
            SimpleNamespace(identifier="video-id"), Quality.Audio.sq
        )
