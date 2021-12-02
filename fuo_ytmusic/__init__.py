from feeluown.app import App
from fuo_ytmusic.provider import YtmusicProvider
from feeluown.uimodels.provider import ProviderUiManager, ProviderUiItem

__alias__ = 'ytmusic'
__version__ = '0.1.1'
__desc__ = 'YouTube Music plugin'

from fuo_ytmusic.ui import YtmusicUiManager

provider = YtmusicProvider()
ui_mgr = None


def enable(app: App):
    global ui_mgr
    app.library.register(provider)
    if app.mode & app.GuiMode:
        ui_mgr = ui_mgr or YtmusicUiManager(app, provider)


def disable(app: App):
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        pass
