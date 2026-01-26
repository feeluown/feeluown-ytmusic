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
- [ ] Discovering page

## Changelog
- v0.4.14 (2026-01-26)
  - 支持 Python 3.14
  - 使用 uv + pyproject.toml 来管理项目
- v0.4.13 (2025-12-13)
  - 修复登录功能
  - 使用 ruff 格式化代码
- v0.4.12 (2025-09-26)
  - 兼容 pyqt6
- v0.4.11 (2025-03-15)
  - 修复纯 CLI 模式不能运行的问题
  - 发布 wheel 包
- v0.4.10 (2025-02-18)
  - 兼容最新的 ytmusicapi 接口
- v0.4.9 (2025-02-04)
  - 默认使用系统 HTTP 代理作为网络代理
  - 修复 `HTTP_PROXY` 配置为空时，yt-dlp 不能使用系统代理的问题
- v0.4.8 (2025-01-31)
  - 使用 yt-dlp 作为获取音源的工具
- v0.4.7 (2025-01-15)
  - 移除 feeluown.uimodels 的依赖
- v0.4.6 (2024-12-01)
  - 修复获取专辑详细信息失败的问题
- v0.4.5 (2024-11-14)
  - 简化登录窗口（之前登录窗口的部分按钮功能实际上不可用）
    - 注：由于 https://github.com/sigma67/ytmusicapi/issues/676，当前登录功能不可用
  - 修复登录失败导致整个插件不可用的问题
- v0.4.4 (2024-08-18)
  - 修复包版本不对的问题
- v0.4.3 (2024-07-25)
  - 修复代理设置失效的问题（该问题导致该插件几乎处于不可用状态）
- v0.4.2 (2024-07-25)
  - 发布失败，tag 打错了
- v0.4.1 (2024-06-25)
  - 实现 SupportsVideoWebUrl 接口
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
