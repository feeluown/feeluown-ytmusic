import json
from pathlib import Path

from feeluown.gui.widgets.login import InvalidCookies, CookiesLoginDialog
from feeluown.uimodels.provider import ProviderUiManager
from feeluown.utils import aio

from fuo_ytmusic import YtmusicProvider
from fuo_ytmusic.consts import HEADER_FILE, REQUIRED_COOKIE_FIELDS


class YtmusicUiManager:
    def __init__(self, app, provider: YtmusicProvider):
        self._app = app
        self._provider = provider
        self._pvd_uimgr: ProviderUiManager = app.pvd_uimgr
        self._pvd_item = self._pvd_uimgr.create_item(
            name=provider.identifier,
            text=provider.name,
            desc=provider.name,
            colorful_svg=(Path(__file__).parent / 'assets' / 'icon.svg').as_posix()
        )
        self._pvd_item.clicked.connect(self.login_or_show)
        self._pvd_uimgr.add_item(self._pvd_item)

    def login_or_show(self):
        if self._provider.user is None:
            dialog = LoginDialog(self._provider)
            dialog.login_succeed.connect(self.load_user)
            dialog.show()
            dialog.autologin()

    def load_user(self):
        user = self._provider.user
        self._app.ui.left_panel.my_music_con.show()
        self._app.ui.left_panel.playlists_con.show()
        self._app.pl_uimgr.clear()
        # self._app.pl_uimgr.add(user.playlists)
        self._pvd_item.text = f'{user.name} - 已登录'


class LoginDialog(CookiesLoginDialog):
    def __init__(self, provider):
        super(LoginDialog, self).__init__(uri='https://music.youtube.com/',
                                          required_cookies_fields=REQUIRED_COOKIE_FIELDS)
        self._provider = provider

    def setup_user(self, user):
        self._provider.user = user

    async def user_from_cookies(self, cookies):
        return self._provider.user_from_cookie(cookies)

    def load_user_cookies(self):
        if HEADER_FILE.exists():
            with HEADER_FILE.open('r') as f:
                return self._parse_text_cookies(json.load(f).get('Cookie', ''))

    def dump_user_cookies(self, user, cookies):
        js = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'X-Goog-AuthUser': '0',
            'x-origin': 'https://music.youtube.com',
            'Cookie': ';'.join([f'{k}={v}' for k, v in cookies.items()])
        }
        with HEADER_FILE.open('w') as f:
            json.dump(js, f, indent=2)
