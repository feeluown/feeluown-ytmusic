import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from feeluown.library import SearchType
from ytmusicapi.exceptions import YTMusicServerError

from fuo_ytmusic import service
from fuo_ytmusic.models import YtmusicSearchAlbum, YtmusicSearchSong


class TestService:
    def setup_method(self):
        service.logger.addHandler(logging.StreamHandler())
        service.logger.setLevel(logging.DEBUG)
        self.service = service.YtmusicService()
        self.service._api = None
        self.service._anonymous_lyrics_api = None
        self.service._anonymous_lyrics_api_lock = threading.Lock()
        self.service._create_api = service.YtmusicService._create_api.__get__(
            self.service,
            service.YtmusicService,
        )

    def teardown_method(self):
        del self.service

    def _set_lyrics_api(self, api):
        self.service._api = api
        self.service._anonymous_lyrics_api = api

    def test_ytmusic_type(self):
        assert service.YtmusicType.parse(SearchType.so) == service.YtmusicType.so
        assert service.YtmusicType.parse(SearchType.al) == service.YtmusicType.al
        assert service.YtmusicType.parse(SearchType.ar) == service.YtmusicType.ar
        assert service.YtmusicType.parse(SearchType.pl) == service.YtmusicType.pl
        assert service.YtmusicType.parse(SearchType.vi) == service.YtmusicType.vi

    def test_search_song(self):
        self.service._api = _StubApi(
            [
                {
                    "category": "Songs",
                    "resultType": "song",
                    "title": "21 Guns",
                    "album": {"id": "ALB1", "name": "21st Century Breakdown"},
                    "feedbackTokens": {},
                    "videoId": "VID1",
                    "isAvailable": True,
                    "isExplicit": False,
                    "artists": [{"id": "AR1", "name": "Green Day"}],
                    "thumbnails": [
                        {
                            "url": "https://example.com/1.jpg",
                            "width": 100,
                            "height": 100,
                        }
                    ],
                    "duration": "3:50",
                }
            ]
        )
        result = self.service.search("21 Guns", service.YtmusicType.so)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchSong) for r in result)

    def test_search_album(self):
        self.service._api = _StubApi(
            [
                {
                    "category": "Albums",
                    "resultType": "album",
                    "title": "ALIN",
                    "type": "Album",
                    "year": "2020",
                    "browseId": "ALB2",
                    "isExplicit": False,
                    "artists": [{"id": "AR2", "name": "A-Lin"}],
                    "thumbnails": [
                        {
                            "url": "https://example.com/2.jpg",
                            "width": 100,
                            "height": 100,
                        }
                    ],
                }
            ]
        )
        result = self.service.search("ALIN", service.YtmusicType.al)
        assert isinstance(result, list)
        assert all(isinstance(r, YtmusicSearchAlbum) for r in result)

    def test_get_charts_returns_raw_dict(self):
        self.service.get_charts.cache_clear()
        self.service._api = _ChartsApi(payload={"videos": []})

        assert self.service.get_charts("ZZ") == {"videos": []}

    def test_get_charts_returns_empty_when_payload_invalid(self):
        self.service.get_charts.cache_clear()
        self.service._api = _ChartsApi(payload=[{"playlistId": "PL-1"}])

        assert self.service.get_charts("ZZ") == {}

    def test_song_lyrics_returns_none_for_plain_text_payload(self):
        self._set_lyrics_api(
            _LyricsApi(
                watch_playlist={"lyrics": "MPLYt_lyrics"},
                lyrics_payload={"lyrics": "line 1\nline 2", "hasTimestamps": False},
            )
        )

        assert self.service.song_lyrics("video-id") is None

    def test_song_lyrics_uses_anonymous_api_when_auth_api_rejects_timed_lyrics(self):
        auth_api = _LyricsApi(
            watch_playlist={"lyrics": "MPLYt_lyrics"},
            lyrics_error=YTMusicServerError(
                "Server returned HTTP 400: Bad Request.\n"
                "Request contains an invalid argument."
            ),
        )
        anonymous_api = _LyricsApi(
            watch_playlist={"lyrics": "MPLYt_lyrics"},
            lyrics_payload={
                "lyrics": [SimpleNamespace(text="anonymous line", start_time=1000)],
                "hasTimestamps": True,
            },
        )
        self.service._api = auth_api
        self.service._anonymous_lyrics_api = anonymous_api

        assert self.service.song_lyrics("video-id") == "[00:01.00]anonymous line"
        assert auth_api.lyrics_requested is False
        assert anonymous_api.lyrics_requested is True

    def test_anonymous_lyrics_api_initializes_once_across_threads(self):
        api = object()
        create_count = 0
        create_count_lock = threading.Lock()
        create_started = threading.Event()
        release_create = threading.Event()

        def create_api(headerfile, _session):
            nonlocal create_count
            assert headerfile is None
            with create_count_lock:
                create_count += 1
            create_started.set()
            release_create.wait(timeout=1)
            return api

        self.service._create_api = create_api

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self.service._get_anonymous_lyrics_api)
                for _ in range(8)
            ]
            assert create_started.wait(timeout=1)
            release_create.set()
            results = [future.result(timeout=1) for future in futures]

        assert create_count == 1
        assert results == [api] * 8

    def test_song_lyrics_returns_none_for_plain_object_payload(self):
        self._set_lyrics_api(
            _LyricsApi(
                watch_playlist={"lyrics": "MPLYt_lyrics"},
                lyrics_payload=SimpleNamespace(lyrics="object lyric"),
            )
        )

        assert self.service.song_lyrics("video-id") is None

    def test_song_lyrics_formats_timestamped_lines_as_lrc(self):
        self._set_lyrics_api(
            _LyricsApi(
                watch_playlist={"lyrics": "MPLYt_lyrics"},
                lyrics_payload={
                    "lyrics": [
                        SimpleNamespace(text="first line", start_time=9200),
                        SimpleNamespace(text="second line", start_time=10680),
                    ],
                    "hasTimestamps": True,
                },
            )
        )

        assert (
            self.service.song_lyrics("video-id")
            == "[00:09.20]first line\n[00:10.68]second line"
        )

    def test_song_lyrics_formats_raw_timestamped_lines_as_lrc(self):
        self._set_lyrics_api(
            _LyricsApi(
                watch_playlist={"lyrics": "MPLYt_lyrics"},
                lyrics_payload={
                    "lyrics": [
                        {
                            "lyricLine": "raw line",
                            "cueRange": {"startTimeMilliseconds": "61500"},
                        }
                    ],
                    "hasTimestamps": True,
                },
            )
        )

        assert self.service.song_lyrics("video-id") == "[01:01.50]raw line"

    def test_song_lyrics_returns_none_without_browse_id(self):
        self._set_lyrics_api(_LyricsApi(watch_playlist={"lyrics": None}))

        assert self.service.song_lyrics("video-id") is None

    def test_song_lyrics_uses_raw_next_response_and_ignores_related_tab(self):
        api = _RawLyricsApi(
            watch_response=_watch_response("MPLYt_lyrics", related_has_endpoint=False),
            lyrics_payload={
                "lyrics": [SimpleNamespace(text="raw lyric", start_time=1000)],
                "hasTimestamps": True,
            },
        )
        self._set_lyrics_api(api)

        assert self.service.song_lyrics("video-id") == "[00:01.00]raw lyric"
        assert api.timestamps_requested is True

    def test_song_lyrics_returns_none_when_raw_lyrics_tab_has_no_endpoint(self):
        api = _RawLyricsApi(
            watch_response=_watch_response(None, related_has_endpoint=False),
            lyrics_payload={"lyrics": "should not be requested"},
        )
        self._set_lyrics_api(api)

        assert self.service.song_lyrics("video-id") is None
        assert api.lyrics_requested is False

    def test_song_lyrics_returns_none_when_timestamped_request_is_invalid(self):
        self._set_lyrics_api(
            _LyricsApi(
                watch_playlist={"lyrics": "MPLYt_lyrics"},
                lyrics_error=YTMusicServerError(
                    "Server returned HTTP 400: Bad Request.\n"
                    "Request contains an invalid argument."
                ),
            )
        )

        assert self.service.song_lyrics("video-id") is None


class _StubApi:
    def __init__(self, payload):
        self._payload = payload

    def search(self, *_args, **_kwargs):
        return list(self._payload)


class _ChartsApi:
    def __init__(self, payload):
        self.payload = payload

    def get_charts(self, *_args, **_kwargs):
        return self.payload


class _LyricsApi:
    def __init__(self, watch_playlist, lyrics_payload=None, lyrics_error=None):
        self.watch_playlist = watch_playlist
        self.lyrics_payload = lyrics_payload
        self.lyrics_error = lyrics_error
        self.lyrics_requested = False
        self.timestamps_requested = None

    def get_watch_playlist(self, video_id):
        assert video_id == "video-id"
        return self.watch_playlist

    def get_lyrics(self, browse_id, timestamps=False):
        assert browse_id == "MPLYt_lyrics"
        self.lyrics_requested = True
        self.timestamps_requested = timestamps
        if self.lyrics_error is not None:
            raise self.lyrics_error
        return self.lyrics_payload


class _RawLyricsApi(_LyricsApi):
    def __init__(self, watch_response, lyrics_payload=None):
        super().__init__(watch_playlist=None, lyrics_payload=lyrics_payload)
        self.watch_response = watch_response

    def send_api_request(self, endpoint, body):
        assert endpoint == "next"
        assert body["videoId"] == "video-id"
        assert body["playlistId"] == "RDAMVMvideo-id"
        assert body["isAudioOnly"] is True
        return self.watch_response

    def get_watch_playlist(self, _video_id):
        raise AssertionError("song_lyrics should use raw next response")


def _watch_response(lyrics_browse_id, related_has_endpoint=True):
    lyrics_tab = {"tabRenderer": {"title": "Lyrics"}}
    if lyrics_browse_id:
        lyrics_tab["tabRenderer"]["endpoint"] = {
            "browseEndpoint": {"browseId": lyrics_browse_id}
        }

    related_tab = {"tabRenderer": {"title": "Related"}}
    if related_has_endpoint:
        related_tab["tabRenderer"]["endpoint"] = {
            "browseEndpoint": {"browseId": "MPLYt_related"}
        }

    return {
        "contents": {
            "singleColumnMusicWatchNextResultsRenderer": {
                "tabbedRenderer": {
                    "watchNextTabbedResultsRenderer": {
                        "tabs": [
                            {"tabRenderer": {"title": "Queue"}},
                            lyrics_tab,
                            related_tab,
                        ]
                    }
                }
            }
        }
    }
