# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['feeluown_ytmusic']

package_data = \
{'': ['*'], 'feeluown_ytmusic': ['assets/*']}

install_requires = \
['cachetools', 'feeluown>=3.7.13', 'ipython', 'pydantic', 'ytmusicapi']

entry_points = \
{'fuo.plugins_v1': ['ytmusic = fuo_ytmusic']}

setup_kwargs = {
    'name': 'feeluown-ytmusic',
    'version': '0.1.0',
    'description': 'feeluown Youtube Music plugin',
    'long_description': '# YouTube Music plugin for FeelUOwn player\n',
    'author': 'Bruce Zhang',
    'author_email': 'zttt183525594@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://github.com/BruceZhang1993/feeluown-ytmusic',
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'entry_points': entry_points,
    'python_requires': '>=3.7,<4.0',
}


setup(**setup_kwargs)

