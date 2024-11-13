import asyncio
import logging
import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QAction, QInputDialog, QMessageBox, QVBoxLayout, QPushButton
from feeluown.utils.aio import run_afn, run_fn
from feeluown.gui.widgets.login import LoginDialog as LoginDialog_
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


class LoginDialog(LoginDialog_):
    def __init__(self, provider):
        super().__init__()

        self._provider = provider

        self._layout = QVBoxLayout(self)
        self._login_btn = QPushButton('登录')
        self.__hint_label = QLabel(
            '请在终端运行 `ytmusicapi oauth` 命令来生成登陆所需信息。'
            '你如果登陆成功，它会在运行命令的目录生成一个 oauth.json 文件，'
            '这个文件包含登录所需的认证信息，你需要把该认证文件移动到 '
            '~/.FeelUOwn/data/ytmusic_header.json ，'
            '然后点击登录。'
        )
        self.__hint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.__progress_label = QLabel()
        self.__hint_label.setWordWrap(True)
        self.__progress_label.setWordWrap(True)
        self._layout.addWidget(self.__hint_label)
        self._layout.addWidget(self.__progress_label)
        self._layout.addWidget(self._login_btn)
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)

        self._login_btn.clicked.connect(lambda: run_afn(self.login))

    def autologin(self):
        if HEADER_FILE.exists():
            run_afn(self.login)
        else:
            self.show_progress(f'请按照上述指南登录...', color='blue')

    async def login(self):
        """Overload super.autologin."""
        if HEADER_FILE.exists():
            with HEADER_FILE.open('r') as f:
                try:
                    oauth = json.load(f)
                except Exception as e:
                    self.show_progress(f'该 json 文件无效：{e}', color='red')
                    return
            self.show_progress('正在尝试加载已有用户...', color='green')
            user = self._provider.user_from_cookie(oauth)
            self._provider.user = user
            try:
                await run_fn(self._provider.library_playlists)
            except Exception as e:
                logger.exception('Try to get user playlists failed')
                self.show_progress(f'获取用户歌单失败：{e}。该认证信息可能无效。', color='red')
                self._provider.user = None
            else:
                self.login_succeed.emit()
        else:
            self.show_progress(f'{HEADER_FILE} 文件不存在', color='red')

    def show_progress(self, text, color='black'):
        if color is None:
            color = ''
        self.__progress_label.setText(f"<p style='color: {color}'>{text}</p>")
