from feeluown.app import App

__alias__ = 'ytmusic'
__version__ = '0.1.1'
__desc__ = 'YouTube Music plugin'


ui_mgr = None


def enable(app: App):
    global ui_mgr

    from fuo_ytmusic.ui import YtmusicUiManager
    from fuo_ytmusic.provider import provider

    app.library.register(provider)
    if app.mode & app.GuiMode:
        ui_mgr = ui_mgr or YtmusicUiManager(app)


def disable(app: App):
    global ui_mgr

    provider = app.library.get('ytmusic')
    if provider is not None:
        app.library.deregister(provider)
    ui_mgr = None
