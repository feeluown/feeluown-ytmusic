import logging
from typing import List, Optional, Sequence, Tuple

from feeluown.library import (
    BriefAlbumModel,
    BriefSongModel,
    BriefVideoModel,
    Collection,
    CollectionType,
    PlaylistModel,
)

from fuo_ytmusic.models import YtmusicHomePlaylist, YtmusicHomeSong, YtmusicSearchAlbum

logger = logging.getLogger(__name__)


class YtmusicHomeRecommendationBuilder:
    DEFAULT_SECTION_TITLE = "Recommendations"
    TYPE_TITLE_SUFFIXES = {
        CollectionType.only_songs: "Songs",
        CollectionType.only_playlists: "Playlists",
        CollectionType.only_albums: "Albums",
        CollectionType.only_videos: "Videos",
    }

    def __init__(self, source: str):
        self._source = source

    @staticmethod
    def normalize_limit(limit: Optional[int], default_limit: int) -> int:
        if limit is None:
            return default_limit
        try:
            normalized = int(limit)
        except (TypeError, ValueError):
            return default_limit
        return normalized if normalized > 0 else default_limit

    def build_collections(self, sections: Sequence[dict]) -> List[Collection]:
        collections: List[Collection] = []
        for section in sections or []:
            if not isinstance(section, dict):
                continue
            contents = section.get("contents")
            if not isinstance(contents, list):
                continue

            section_title = section.get("title") or self.DEFAULT_SECTION_TITLE
            typed_collections = self._build_typed_collections(contents)
            if not typed_collections:
                continue
            if len(typed_collections) == 1:
                section_type, models = typed_collections[0]
                collections.append(
                    Collection(name=section_title, type_=section_type, models=models)
                )
                continue
            for section_type, models in typed_collections:
                suffix = self.TYPE_TITLE_SUFFIXES[section_type]
                collections.append(
                    Collection(
                        name=f"{section_title} · {suffix}",
                        type_=section_type,
                        models=models,
                    )
                )
        return collections

    def _build_typed_collections(
        self, contents: Sequence[dict]
    ) -> List[Tuple[CollectionType, list]]:
        type_builder_pairs = [
            (CollectionType.only_songs, self._build_home_songs),
            (CollectionType.only_playlists, self._build_home_playlists),
            (CollectionType.only_albums, self._build_home_albums),
            (CollectionType.only_videos, self._build_home_videos),
        ]
        collections = []
        for section_type, builder in type_builder_pairs:
            models = builder(contents)
            if models:
                collections.append((section_type, models))
        return collections

    @staticmethod
    def _iter_valid_contents(contents: Sequence[dict]):
        for content in contents or []:
            if isinstance(content, dict):
                yield content

    @staticmethod
    def _detect_home_item_type(content: dict):
        playlist_id = content.get("playlistId")
        video_id = content.get("videoId")
        artists = content.get("artists")
        album = content.get("album")

        if playlist_id and not video_id:
            # Includes watch playlist and mix/radio-like playlist rows.
            return CollectionType.only_playlists
        if video_id:
            # Some cards carry both videoId and playlistId. If there is no song
            # metadata, treat them as playlist-like mix cards.
            if playlist_id and not artists and not album:
                return CollectionType.only_playlists
            # YTMusic home videos usually include a view-count field.
            if content.get("views"):
                return CollectionType.only_videos
            return CollectionType.only_songs
        if playlist_id:
            return CollectionType.only_playlists
        if content.get("browseId") and content.get("artists") is not None:
            # Artists also carry browseId; require artists field to identify albums.
            return CollectionType.only_albums
        return None

    def _build_home_songs(self, contents: Sequence[dict]) -> List[BriefSongModel]:
        songs: List[BriefSongModel] = []
        seen_video_ids = set()
        for content in self._iter_valid_contents(contents):
            if self._detect_home_item_type(content) != CollectionType.only_songs:
                continue
            video_id = content.get("videoId")
            if not video_id or video_id in seen_video_ids:
                continue
            try:
                song = YtmusicHomeSong(**content).v2_brief_model()
            except Exception as e:
                logger.warning("skip invalid home song item(%s): %s", video_id, e)
                continue
            if not song.identifier:
                continue
            seen_video_ids.add(song.identifier)
            songs.append(song)
        return songs

    def _build_home_playlists(self, contents: Sequence[dict]) -> List[PlaylistModel]:
        playlists: List[PlaylistModel] = []
        seen_playlist_ids = set()
        for content in self._iter_valid_contents(contents):
            if self._detect_home_item_type(content) != CollectionType.only_playlists:
                continue
            playlist_id = content.get("playlistId")
            if not playlist_id or playlist_id in seen_playlist_ids:
                continue
            try:
                playlist = YtmusicHomePlaylist(**content).v2_model()
            except Exception as e:
                logger.warning("skip invalid home playlist item(%s): %s", playlist_id, e)
                continue
            if not playlist.identifier:
                continue
            seen_playlist_ids.add(playlist.identifier)
            playlists.append(playlist)
        return playlists

    def _build_home_albums(self, contents: Sequence[dict]) -> List[BriefAlbumModel]:
        albums: List[BriefAlbumModel] = []
        seen_browse_ids = set()
        for content in self._iter_valid_contents(contents):
            if self._detect_home_item_type(content) != CollectionType.only_albums:
                continue
            browse_id = content.get("browseId")
            if not browse_id or browse_id in seen_browse_ids:
                continue
            try:
                album = YtmusicSearchAlbum(**content).v2_brief_model()
            except Exception as e:
                logger.warning("skip invalid home album item(%s): %s", browse_id, e)
                continue
            if not album.identifier:
                continue
            seen_browse_ids.add(album.identifier)
            albums.append(album)
        return albums

    def _build_home_videos(self, contents: Sequence[dict]) -> List[BriefVideoModel]:
        videos: List[BriefVideoModel] = []
        seen_video_ids = set()
        for content in self._iter_valid_contents(contents):
            if self._detect_home_item_type(content) != CollectionType.only_videos:
                continue
            video_id = content.get("videoId")
            if not video_id or video_id in seen_video_ids:
                continue
            artists = content.get("artists")
            artists_name = " / ".join(
                artist.get("name", "")
                for artist in (artists or [])
                if isinstance(artist, dict) and artist.get("name")
            )
            videos.append(
                BriefVideoModel(
                    identifier=video_id,
                    source=self._source,
                    title=content.get("title") or "",
                    artists_name=artists_name,
                    duration_ms=content.get("duration") or "",
                )
            )
            seen_video_ids.add(video_id)
        return videos
