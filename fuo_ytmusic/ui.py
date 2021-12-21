import asyncio
import json
import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QAction, QInputDialog, QMessageBox
from feeluown.gui.widgets.login import CookiesLoginDialog
from feeluown.uimodels.my_music import MyMusicUiManager
from feeluown.uimodels.playlist import PlaylistUiManager
from feeluown.uimodels.provider import ProviderUiManager

from fuo_ytmusic.consts import HEADER_FILE, REQUIRED_COOKIE_FIELDS

from .page_explore_qml import render as explore_render
from .page_fav import render as fav_render
from .page_more import render as more_render
from .service import YtmusicPrivacyStatus


class YtmusicUiManager:
    def __init__(self, app):
        self._app = app
        self._provider = app.library.get('ytmusic')
        self._pvd_uimgr: ProviderUiManager = app.pvd_uimgr
        self._pvd_item = self._pvd_uimgr.create_item(
            name=self._provider.identifier,
            text=self._provider.name,
            desc=self._provider.name,
            colorful_svg=(Path(__file__).parent / 'assets' / 'icon.svg').as_posix()
        )
        self._pvd_item.clicked.connect(self.login_or_show)
        self._pvd_uimgr.add_item(self._pvd_item)
        self._app.browser.route('/providers/ytmusic/fav')(fav_render)
        self._app.browser.route('/providers/ytmusic/explore')(explore_render)
        self._app.browser.route('/providers/ytmusic/more')(more_render)

    def login_or_show(self):
        if self._provider.user is None:
            dialog = LoginDialog(self._provider)
            dialog.login_succeed.connect(lambda: asyncio.ensure_future(self.load_user()))
            dialog.show()
            dialog.autologin()
        else:
            asyncio.ensure_future(self.load_user())

    def new_playlist(self):
        name, o1 = QInputDialog.getText(self._app.ui.left_panel.playlists_header, '新建歌单', '请输入歌单名称:')
        if not o1:
            return
        desc, o2 = QInputDialog.getText(self._app.ui.left_panel.playlists_header, '新建歌单', '请输入歌单描述:')
        if not o2:
            return
        privacy_status, o3 = QInputDialog.getItem(self._app.ui.left_panel.playlists_header, '新建歌单', '请选择歌单权限:',
                                                  [i.value for i in YtmusicPrivacyStatus])
        if not o3:
            return
        ok = self._provider.create_playlist(name, desc, YtmusicPrivacyStatus.parse(privacy_status))
        if not ok:
            QMessageBox.warning(self._app.ui.left_panel.playlists_header, '新建歌单', '创建失败！')
        else:
            QMessageBox.information(self._app.ui.left_panel.playlists_header, '新建歌单', '创建成功！')

    async def load_user(self):
        user = self._provider.user
        self._app.ui.left_panel.playlists_con.show()
        self._app.ui.left_panel.my_music_con.show()

        # hack fuo to support add playlist
        pl_header: QLabel = self._app.ui.left_panel.playlists_header
        pl_header.setContextMenuPolicy(Qt.ActionsContextMenu)
        for a in pl_header.actions():
            pl_header.removeAction(a)
        new_pl_action = QAction('新建歌单', pl_header)
        pl_header.addAction(new_pl_action)
        new_pl_action.triggered.connect(self.new_playlist)

        mymusic_mgr: MyMusicUiManager = self._app.mymusic_uimgr
        playlists_mgr: PlaylistUiManager = self._app.pl_uimgr

        explore_item = mymusic_mgr.create_item('🔮 发现音乐')
        my_fav_item = mymusic_mgr.create_item('⭐️ 收藏与关注')
        more_item = mymusic_mgr.create_item('☁️ 上传的音乐')
        explore_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/explore'), weak=False)
        my_fav_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/fav'), weak=False)
        more_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/more'), weak=False)
        mymusic_mgr.clear()
        mymusic_mgr.add_item(explore_item)
        mymusic_mgr.add_item(my_fav_item)
        mymusic_mgr.add_item(more_item)

        playlists_mgr.clear()
        self._pvd_item.text = f'{user.name} - 已登录'

        loop = asyncio.get_event_loop()
        pls = await loop.run_in_executor(None, self._provider.library_playlists)
        playlists_mgr.add(pls)


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
            'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'X-Goog-AuthUser': '0',
            'x-origin': 'https://music.youtube.com',
            'Cookie': ';'.join([f'{k}={v}' for k, v in cookies.items()])
        }
        with HEADER_FILE.open('w') as f:
            json.dump(js, f, indent=2)
