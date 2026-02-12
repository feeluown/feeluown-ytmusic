# YouTube Music plugin for FeelUOwn player

## Prerequisites

Install [FeelUOwn](https://github.com/feeluown/FeelUOwn) before installing this plugin.
Sees: [Documentation](https://feeluown.readthedocs.io/)

## Installation

```shell
pip install fuo-ytmusic  # Lastest stable release
pip install https://github.com/feeluown/feeluown-ytmusic.git  # master branch
uv sync  # Local development
```

## Configuration

```python
# In ~/.fuorc
config.ytmusic.HTTP_PROXY='http://127.0.0.1:7890'
```

## Contributing

Pull requests are welcome. For major changes, please create a new issue first to discuss what you'd like to change.

Please make sure to compatible with [FeelUOwn](https://github.com/feeluown/FeelUOwn) lastest stable release.

## Roadmap

- [x] Show album/artist/playlist
- [x] Play song/mv/video
- [x] Login with web cookies or `ytmusicapi oauth`
- [x] Get song detail by id
- [ ] Add/remove song from a playlist
- [ ] Upload songs to cloud
- [x] Daily recommendation page (songs/playlists)
- [ ] Discovering page

## Changelog
- v0.4.15 (2026-02-03)
  - Support multi-profile switching
  - Sync auto-login profile selection
- v0.4.14 (2026-01-26)
  - Support Python 3.14
  - Manage the project with uv + pyproject.toml
- v0.4.13 (2025-12-13)
  - Fix login flow
  - Format code with ruff
- v0.4.12 (2025-09-26)
  - Compatible with pyqt6
- v0.4.11 (2025-03-15)
  - Fix CLI-only mode not working
  - Publish wheel package
- v0.4.10 (2025-02-18)
  - Compatible with latest ytmusicapi
- v0.4.9 (2025-02-04)
  - Use system HTTP proxy by default
  - Fix yt-dlp not using system proxy when `HTTP_PROXY` is empty
- v0.4.8 (2025-01-31)
  - Use yt-dlp to fetch media
- v0.4.7 (2025-01-15)
  - Remove dependency on feeluown.uimodels
- v0.4.6 (2024-12-01)
  - Fix album detail fetch failures
- v0.4.5 (2024-11-14)
  - Simplify login window (some buttons were not functional)
    - Note: login currently unavailable due to https://github.com/sigma67/ytmusicapi/issues/676
  - Fix plugin unusable when login fails
- v0.4.4 (2024-08-18)
  - Fix incorrect package version
- v0.4.3 (2024-07-25)
  - Fix proxy settings not taking effect (plugin was nearly unusable)
- v0.4.2 (2024-07-25)
  - Release failed due to wrong tag
- v0.4.1 (2024-06-25)
  - Implement SupportsVideoWebUrl
- v0.4.0 (2024-06-25)
  - Stop returning unavailable playback URLs (pytube broken)
- v0.3.4 (2024-01-21)
  - Fix playback URLs failing due to IP changes
  - Remove unreasonable caching logic
- v0.3.3 (2024-01-15)
  - Fix over-reliance on fuo-netease
  - Fix intermittent song URL fetch failures
- v0.3.2 (2023-12-03)
  - Fix expired key issues
- v0.3.1 (2023-08-15)
  - remove the 'pytube' dependency
- v0.3.0 (2023-07-18)
  - use pydantic>=2.0
- v0.2.3 (2023-07-15)
  - fix loading header_file failed
- v0.2.2 (2023-07-13)
  - fix can't get song media properly

## License

This project is licensed under the [GPLv3](LICENSE.txt).
