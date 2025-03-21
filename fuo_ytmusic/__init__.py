from urllib.request import getproxies

from feeluown.app import App

__alias__ = 'ytmusic'
__version__ = '0.3.0'
__desc__ = 'YouTube Music plugin'


ui_mgr = None


def init_config(config):
    # For example: http://127.0.0.1:7890. This will be used in API and media accessing.
    config.deffield('HTTP_PROXY', type_=str, default='', desc='YouTube Music HTTP proxy')
    config.deffield('HTTP_TIMEOUT', type_=int, default=2, desc='HTTP requests timeout')


def enable(app: App):
    global ui_mgr

    from fuo_ytmusic.provider import provider

    # Use system http proxy by default.
    sys_proxies = getproxies()
    sys_http_proxy = sys_proxies.get('http')
    config_http_proxy = app.config.ytmusic.HTTP_PROXY
    if not config_http_proxy and sys_http_proxy:
        config_http_proxy = sys_http_proxy

    provider.setup_http_proxy(config_http_proxy)
    provider.setup_http_timeout(app.config.ytmusic.HTTP_TIMEOUT)
    app.library.register(provider)
    if app.mode & app.GuiMode:
        from fuo_ytmusic.ui import YtmusicUiManager
        ui_mgr = ui_mgr or YtmusicUiManager(app)


def disable(app: App):
    global ui_mgr

    provider = app.library.get('ytmusic')
    if provider is not None:
        app.library.deregister(provider)
    ui_mgr = None
