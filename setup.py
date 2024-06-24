# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['fuo_ytmusic']

package_data = \
{'': ['*'], 'fuo_ytmusic': ['assets/*', 'qml/*', 'qml/dummydata/*']}

install_requires = \
['cachetools', 'feeluown>=3.7.13', 'pydantic', 'ytmusicapi']

entry_points = \
{'fuo.plugins_v1': ['ytmusic = fuo_ytmusic']}

setup_kwargs = {
    'name': 'fuo-ytmusic',
    'version': '0.4.0',
    'description': 'feeluown Youtube Music plugin',
    'long_description': "# YouTube Music plugin for FeelUOwn player\n\n## Prerequisites\n\nInstall [FeelUOwn](https://github.com/feeluown/FeelUOwn) before installing this plugin.\nSees: [Documentation](https://feeluown.readthedocs.io/)\n\n## Installation\n\n```shell\npip install fuo-ytmusic  # Lastest stable release\npip install https://github.com/feeluown/feeluown-ytmusic.git  # master branch\npoetry install  # Local development\n```\n\n## Configuration\n\n### Proxies\n\n```python\n# In ~/.fuorc\nconfig.deffield('YTM_HTTP_PROXY', type_=str, default='', desc='YouTube Music 代理设置')\nconfig.YTM_HTTP_PROXY='127.0.0.1:10809'\n```\n\n## Contributing\n\nPull requests are welcome. For major changes, please create a new issue first to discuss what you'd like to change.\n\nPlease make sure to compatible with [FeelUOwn](https://github.com/feeluown/FeelUOwn) lastest stable release.\n\n## License\n\nThis project is licensed under the [GPLv3](LICENSE.txt).\n",
    'author': 'Bruce Zhang',
    'author_email': 'zttt183525594@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://github.com/feeluown/feeluown-ytmusic',
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'entry_points': entry_points,
    'python_requires': '>=3.7,<4.0',
}


setup(**setup_kwargs)
