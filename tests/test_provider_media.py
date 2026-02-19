import copy
from types import SimpleNamespace

import pytest
from feeluown.excs import ProviderIOError
from feeluown.media import MediaType, Quality
from yt_dlp import DownloadError

from fuo_ytmusic import provider as provider_module
from fuo_ytmusic.provider import YtmusicProvider, _parse_ytdlp_version


class _ApiStub:
    def __init__(self, user_agent="", headerfile_path=None):
        self._user_agent = user_agent
        self.headerfile_path = headerfile_path

    def get_user_agent(self):
        return self._user_agent


class _ServiceStub:
    def __init__(self, api):
        self.api = api
        self.timeout = None

    def get_user_agent(self):
        return self.api.get_user_agent()

    def setup_timeout(self, timeout):
        self.timeout = timeout


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


class _YtdlpCaptureVideo:
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
            "formats": [
                {
                    "url": "https://cdn.example.com/audio.m4a",
                    "acodec": "mp4a.40.2",
                    "abr": 128,
                },
                {
                    "url": "https://cdn.example.com/video.mp4",
                    "vcodec": "avc1.4d401f",
                    "width": 1280,
                    "protocol": "https",
                },
            ]
        }


def test_song_get_media_passes_cookiefile_and_user_agent_to_ytdlp(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub(user_agent="ytmusic-agent"))
    monkeypatch.setattr(
        provider, "_get_ytdlp_cookiefile_path", lambda: "/tmp/ytmusic.cookies.txt"
    )
    monkeypatch.setattr(provider_module, "_NoCookieSaveYoutubeDL", _YtdlpCapture)

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
    monkeypatch.setattr(provider, "_get_ytdlp_cookiefile_path", lambda: "")
    monkeypatch.setattr(provider_module, "_NoCookieSaveYoutubeDL", _YtdlpCapture)

    provider.song_get_media(SimpleNamespace(identifier="video-id"), Quality.Audio.sq)

    assert "cookiefile" not in _YtdlpCapture.last_opts
    assert "user_agent" not in _YtdlpCapture.last_opts


def test_song_get_media_raises_user_actionable_error(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub())
    monkeypatch.setattr(
        provider, "_get_ytdlp_cookiefile_path", lambda: "/tmp/ytmusic.cookies.txt"
    )
    monkeypatch.setattr(provider_module, "_NoCookieSaveYoutubeDL", _YtdlpFailure)

    with pytest.raises(ProviderIOError, match="cookies may be expired"):
        provider.song_get_media(
            SimpleNamespace(identifier="video-id"), Quality.Audio.sq
        )


def test_song_get_media_uses_configured_timeout(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub())
    provider.setup_http_timeout(8)
    monkeypatch.setattr(provider, "_get_ytdlp_cookiefile_path", lambda: "")
    monkeypatch.setattr(provider_module, "_NoCookieSaveYoutubeDL", _YtdlpCapture)

    provider.song_get_media(SimpleNamespace(identifier="video-id"), Quality.Audio.sq)

    assert _YtdlpCapture.last_opts["socket_timeout"] == 8
    assert provider.service.timeout == 8


def test_video_get_media_uses_configured_timeout(monkeypatch):
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub())
    provider.setup_http_timeout(8)
    monkeypatch.setattr(provider, "_get_ytdlp_cookiefile_path", lambda: "")
    monkeypatch.setattr(provider_module, "_NoCookieSaveYoutubeDL", _YtdlpCaptureVideo)

    provider.video_get_media(SimpleNamespace(identifier="video-id"), Quality.Video.sd)

    assert _YtdlpCaptureVideo.last_opts["socket_timeout"] == 8
    assert "cookiefile" not in _YtdlpCaptureVideo.last_opts


def test_get_ytdlp_cookiefile_path_requires_current_user(tmp_path):
    headerfile = tmp_path / "ytmusic_header.json"
    headerfile.write_text("{}", encoding="utf-8")
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub(headerfile_path=headerfile))

    assert provider._get_ytdlp_cookiefile_path() == ""

    provider._user = object()
    assert provider._get_ytdlp_cookiefile_path() == str(
        tmp_path / "ytmusic_header.cookies.txt"
    )


def test_get_ytdlp_cookiefile_path_disabled_for_new_ytdlp_version(
    monkeypatch, tmp_path
):
    headerfile = tmp_path / "ytmusic_header.json"
    headerfile.write_text("{}", encoding="utf-8")
    provider = YtmusicProvider()
    provider.service = _ServiceStub(_ApiStub(headerfile_path=headerfile))
    provider._user = object()
    monkeypatch.setattr(provider_module, "YTDLP_VERSION", "2026.02.04")

    assert provider._get_ytdlp_cookiefile_path() == ""


def test_parse_ytdlp_version():
    assert _parse_ytdlp_version("2026.02.04") == (2026, 2, 4)
    assert _parse_ytdlp_version("2025.12.08") == (2025, 12, 8)
    assert _parse_ytdlp_version("invalid") is None
    assert _parse_ytdlp_version("2026.02") is None


def test_img_url_to_media_passes_http_proxy():
    provider = YtmusicProvider()
    provider.setup_http_proxy("http://127.0.0.1:7890")

    media = provider.img_url_to_media("https://img.example.com/cover.jpg")

    assert media.type_ == MediaType.image
    assert media.url == "https://img.example.com/cover.jpg"
    assert media.http_proxy == "http://127.0.0.1:7890"


def test_img_url_to_media_omits_proxy_when_unset(monkeypatch):
    provider = YtmusicProvider()
    captured = {}

    def _media_factory(url, type_, **kwargs):
        captured["url"] = url
        captured["type_"] = type_
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            url=url, type_=type_, http_proxy=kwargs.get("http_proxy", "")
        )

    monkeypatch.setattr(provider_module, "Media", _media_factory)

    media = provider.img_url_to_media("https://img.example.com/cover.jpg")

    assert media.type_ == MediaType.image
    assert media.url == "https://img.example.com/cover.jpg"
    assert "http_proxy" not in captured["kwargs"]
