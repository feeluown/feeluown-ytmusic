from feeluown.app import App

__alias__ = 'ytmusic'
__version__ = '0.1.1'
__desc__ = 'YouTube Music plugin'

from fuo_ytmusic.ui import YtmusicUiManager
from fuo_ytmusic.provider import provider

ui_mgr = None


def enable(app: App):
    global provider, ui_mgr

    app.library.register(provider)
    if app.mode & app.GuiMode:
        ui_mgr = ui_mgr or YtmusicUiManager(app)


def disable(app: App):
    global provider
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        pass
