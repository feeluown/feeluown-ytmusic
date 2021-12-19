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

### Proxies

```python
# In ~/.fuorc
config.deffield('YTM_HTTP_PROXY', type_=str, default='', desc='YouTube Music 代理设置')
config.YTM_HTTP_PROXY='127.0.0.1:10809'
```

## Contributing

Pull requests are welcome. For major changes, please create a new issue first to discuss what you'd like to change.

Please make sure to compatible with [FeelUOwn](https://github.com/feeluown/FeelUOwn) lastest stable release.

## License

This project is licensed under the [GPLv3](LICENSE.txt).
