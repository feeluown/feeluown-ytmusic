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

- v0.4.0 (2024-06-25)
  - 不在返回不可用的播放链接（pytube 失效了）
- v0.3.4 (2024-01-21)
  - 修复由于 IP 变更导致歌曲链接一直失效的问题
  - 移除不太合理的缓存逻辑
- v0.3.3 (2024-01-15)
  - 修复过度依赖 fuo-netease 的问题
  - 修复有时获取歌曲链接一直失败的问题
- v0.3.2 (2023-12-03)
  - 修复密钥过期的问题
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
