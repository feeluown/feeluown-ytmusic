import json
from pathlib import Path

from feeluown.library import AlbumType
from feeluown.media import Quality

from fuo_ytmusic.models import AlbumInfo, ArtistInfo, SongInfo, YtmusicSearchVideo

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name):
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def test_album_info_v2_model_sets_type_and_song_count():
    data = _load_fixture("model_fields_get_album_single.json")
    model = AlbumInfo(**data).v2_model_with_identifier("fixture-album")

    assert model.type_ == AlbumType.single.value
    assert model.song_count == data["trackCount"]


def test_album_info_v2_model_sets_ep_type():
    data = _load_fixture("model_fields_get_album_ep.json")
    model = AlbumInfo(**data).v2_model_with_identifier("fixture-album-ep")

    assert model.type_ == AlbumType.ep.value


def test_search_video_v2_model_sets_play_count_unknown_from_views_text():
    data = _load_fixture("model_fields_artist_video_item.json")
    model = YtmusicSearchVideo(**data).v2_model()

    assert model.play_count == -1


def test_search_video_v2_model_sets_play_count_unknown_from_zh_views_text():
    data = _load_fixture("model_fields_artist_video_item_zh.json")
    model = YtmusicSearchVideo(**data).v2_model()

    assert model.play_count == -1


def test_artist_info_v2_model_sets_hot_songs():
    data = _load_fixture("model_fields_get_artist.json")
    model = ArtistInfo(**data).v2_model("fixture-artist")

    assert len(model.hot_songs) == len(data["songs"]["results"])
    assert model.hot_songs[0].identifier
    assert model.song_count == -1
    assert model.album_count == -1
    assert model.mv_count == -1


def test_artist_info_v2_model_prefers_highest_resolution_thumbnail():
    data = _load_fixture("model_fields_get_artist.json")
    model = ArtistInfo(**data).v2_model("fixture-artist")

    assert model.pic_url == data["thumbnails"][-1]["url"]


def test_song_info_supports_audio_quality_and_media_mapping():
    data = _load_fixture("model_fields_get_song.json")
    song = SongInfo(**data)

    audio_qualities = song.list_formats()
    assert audio_qualities

    target_quality = audio_qualities[0]
    itag, bitrate, mime_type = song.get_media(target_quality)
    assert itag is not None
    assert bitrate is not None
    assert mime_type

    if Quality.Audio.sq in audio_qualities:
        sq_itag, _, _ = song.get_media(Quality.Audio.sq)
        assert sq_itag is not None
