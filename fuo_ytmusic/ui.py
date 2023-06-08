import asyncio
import logging
import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QAction, QInputDialog, QMessageBox, QTextEdit
from feeluown.utils import aio
from feeluown.gui.widgets.login import CookiesLoginDialog
from feeluown.uimodels.my_music import MyMusicUiManager
from feeluown.uimodels.playlist import PlaylistUiManager
from feeluown.uimodels.provider import ProviderUiManager

from fuo_ytmusic.consts import HEADER_FILE, REQUIRED_COOKIE_FIELDS

# QML page has two problems
# 1. they may block the whole UI.
# 2. they consumes much memory.
# from .page_explore_qml import render as explore_render
# from .page_more import render as more_render
from .page_fav import render as fav_render
from .service import YtmusicPrivacyStatus


logger = logging.getLogger(__name__)


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
        # self._app.browser.route('/providers/ytmusic/explore')(explore_render)
        # self._app.browser.route('/providers/ytmusic/more')(more_render)

    def login_or_show(self):
        if self._provider.user is None:
            dialog = LoginDialog(self._provider)
            dialog.login_succeed.connect(lambda: asyncio.ensure_future(self.load_user()))
            dialog.open()
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

        # explore_item = mymusic_mgr.create_item('🔮 发现音乐')
        my_fav_item = mymusic_mgr.create_item('⭐️ 收藏与关注')
        # more_item = mymusic_mgr.create_item('☁️ 上传的音乐')
        # explore_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/explore'), weak=False)
        my_fav_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/fav'), weak=False)
        # more_item.clicked.connect(lambda: self._app.browser.goto(page='/providers/ytmusic/more'), weak=False)
        mymusic_mgr.clear()
        # mymusic_mgr.add_item(explore_item)
        mymusic_mgr.add_item(my_fav_item)
        # mymusic_mgr.add_item(more_item)

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

        self.auth_text_edit = QTextEdit(self)
        self.auth_text_edit.setAcceptRichText(False)
        self.auth_text_edit.setPlaceholderText(
            '请打开 music.youtube.com 并登陆，'
            '然后从浏览器中复制 HTTP 请求 header 中的 Authorization 字段：\n\n'
            '它类似这样：SAPISIDHASH 123333333_abfasdfs12fadcdfa2d'
        )
        self.__hint_label = QLabel(
            '还有另外一种登陆方式，你可以参考 ytmusicapi 的使用文档，使用'
            ' ytmusicapi oauth 命令来生成登陆所需信息。你如果登陆成功，'
            '它会生成一个 oauth.json 文件，你把 oauth.json 文件移动到'
            ' ~/.FeelUOwn/data/ytmusic_header.json ，然后重新点击图标登陆即可。'
        )
        self.__hint_label.setWordWrap(True)
        # weblogin can't fetch the authorization field, so diable it.
        self.weblogin_btn.hide()
        self._layout.insertWidget(0, self.auth_text_edit)
        self._layout.addWidget(self.__hint_label)
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)

    def setup_user(self, user):
        self._provider.user = user

    def get_cookies(self):
        cookie = self.cookies_text_edit.toPlainText()
        auth = self.auth_text_edit.toPlainText()
        if not auth or not cookie:
            self.show_hint(f'authorization is empty, you must fill it', color='orange')
            return None

        agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'
        # Note ytmusicapi needs the entire header, not only the authorization and cookie parts.
        header = {
            "user-agent": agent,
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "content-type": "application/json",
            "content-encoding": "gzip",
            "origin": 'https://music.youtube.com',
            'authorization': auth,
            'cookie': cookie,
        }
        return header

    async def user_from_cookies(self, cookies):
        return self._provider.user_from_cookie(cookies)

    def load_user_cookies(self):
        self.load_header_file()

    def load_header_file(self):
        if HEADER_FILE.exists():
            with HEADER_FILE.open('r') as f:
                data = json.load(f)
                return data

    def autologin(self):
        """Overload super.autologin."""
        header_or_oauth = self.load_header_file()
        if header_or_oauth is not None:
            self.show_hint('正在尝试加载已有用户...', color='green')
            if 'cookie' in header_or_oauth:  # It is a header.
                cookie = header_or_oauth['cookie']
                auth = header_or_oauth['authorization']
                self.cookies_text_edit.setText(cookie)
                self.auth_text_edit.setText(auth)
            else:
                logger.debug('The header file is a oauth.json, will not load it to UI')
            aio.create_task(self.login_with_cookies(header_or_oauth))

    def dump_user_cookies(self, user, cookies):
        with HEADER_FILE.open('w') as f:
            json.dump(cookies, f, indent=2)
