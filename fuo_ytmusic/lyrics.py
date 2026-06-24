from typing import Optional

WATCH_NEXT_RENDERER_PATH = (
    "contents",
    "singleColumnMusicWatchNextResultsRenderer",
    "tabbedRenderer",
    "watchNextTabbedResultsRenderer",
)


def build_watch_playlist_body(video_id: str) -> dict:
    return {
        "enablePersistentPlaylistPanel": True,
        "isAudioOnly": True,
        "tunerSettingValue": "AUTOMIX_SETTING_NORMAL",
        "videoId": video_id,
        "playlistId": f"RDAMVM{video_id}",
        "watchEndpointMusicSupportedConfigs": {
            "watchEndpointMusicConfig": {
                "hasPersistentPlaylistPanel": True,
                "musicVideoType": "MUSIC_VIDEO_TYPE_ATV",
            }
        },
    }


def extract_lyrics_browse_id(watch_response) -> Optional[str]:
    tabs = watch_response
    for key in WATCH_NEXT_RENDERER_PATH:
        tabs = tabs[key]
    tabs = tabs["tabs"]

    try:
        browse_id = tabs[1]["tabRenderer"]["endpoint"]["browseEndpoint"]["browseId"]
    except (IndexError, KeyError, TypeError):
        return None
    if not isinstance(browse_id, str):
        raise TypeError(f"unexpected lyrics browse id type: {type(browse_id)}")
    return browse_id


def timestamped_lyrics_to_lrc(lyrics_payload) -> Optional[str]:
    lyrics = lyrics_payload["lyrics"]
    if not isinstance(lyrics, list):
        return None

    lines = [format_lyric_line(line) for line in lyrics]
    if not lines:
        return None
    return "\n".join(lines)


def format_lyric_line(line) -> str:
    return f"{format_lrc_timestamp(line.start_time)}{line.text}"


def format_lrc_timestamp(milliseconds: int) -> str:
    if not isinstance(milliseconds, int):
        raise TypeError(f"unexpected lyric start_time type: {type(milliseconds)}")
    total_ms = max(0, milliseconds)
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) // 1000
    centiseconds = (total_ms % 1000) // 10
    return f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"
