from pathlib import Path

from feeluown.app import App
from fuo_ytmusic.provider import YtmusicProvider
from feeluown.uimodels.provider import ProviderUiManager, ProviderUiItem

__alias__ = 'ytmusic'
__version__ = '0.1.1'
__desc__ = 'YouTube Music plugin'

provider = YtmusicProvider()
item: ProviderUiItem


def enable(app: App):
    global item
    app.library.register(provider)
    if app.mode & app.GuiMode:
        app.pvd_uimgr: ProviderUiManager
        item = app.pvd_uimgr.create_item(
            name=provider.identifier,
            text=provider.name,
            desc=provider.name,
            colorful_svg=(Path(__file__).parent / 'assets' / 'icon.svg').as_posix()
        )
        app.pvd_uimgr.add_item(item)


def disable(app: App):
    global item
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        app.pvd_uimgr: ProviderUiManager
        app.pvd_uimgr.remove(item)
