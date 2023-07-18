# YouTube Music plugin for FeelUOwn player

## Prerequisites

Install [FeelUOwn](https://github.com/feeluown/FeelUOwn) before installing this plugin.
Sees: [Documentation](https://feeluown.readthedocs.io/)

## Installation

```shell
pip install fuo-ytmusic  # Lastest stable release
pip install https://github.com/feeluown/feeluown-ytmusic.git  # master branch
poetry install  # Local development
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
- [ ] Discovering page

## Changelog

- v0.3.0 (2023-07-18)
  - use pydantic>=2.0
- v0.2.3 (2023-07-15)
  - fix loading header_file failed
- v0.2.2 (2023-07-13)
  - fix can't get song media properly

## License

This project is licensed under the [GPLv3](LICENSE.txt).
