import logging
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMenu
from feeluown.gui.widgets import TextButton
from feeluown.gui.widgets.songs import SongsTableView
from feeluown.utils import aio
from feeluown.gui.base_renderer import LibraryTabRendererMixin
from feeluown.gui.page_containers.table import Renderer
from feeluown.gui.widgets.tabbar import Tab

from fuo_ytmusic import YtmusicProvider

logger = logging.getLogger(__name__)


async def render(req, **kwargs):
    app = req.ctx['app']
    app.ui.right_panel.set_body(app.ui.table_container)

    provider: YtmusicProvider = app.library.get('ytmusic')
    tab_id = Tab(int(req.query.get('tab_id', Tab.songs.value)))
    renderer = FavRenderer(tab_id, provider)
    await app.ui.table_container.set_renderer(renderer)


class FavRenderer(Renderer, LibraryTabRendererMixin):
    def __init__(self, tab_id, provider):
        self.tab_id = tab_id
        self._provider: YtmusicProvider = provider

    async def render(self):
        self.render_tabbar()
        self.meta_widget.show()
        self.meta_widget.title = '上传的音乐'

        if self.tab_id == Tab.songs:
            self.songs_table: SongsTableView
            self.songs_table.remove_song_func = self._delete_song
            self.show_songs(await aio.run_fn(lambda: self._provider.library_upload_songs()))
            self.toolbar.show()
            # self.toolbar.manual_mode()
            btn = TextButton('上传音乐', self.toolbar)
            btn.clicked.connect(self._upload_song)
            self.toolbar.add_tmp_button(btn)
        elif self.tab_id == Tab.artists:
            self.show_artists(await aio.run_fn(lambda: self._provider.library_upload_artists()))
        elif self.tab_id == Tab.albums:
            self.show_albums(await aio.run_fn(lambda: self._provider.library_upload_albums()))

    def _delete_song(self, song):
        entity_id = song.entityId
        ok = self._provider.delete_uploaded_song(entity_id)
        if not ok:
            QMessageBox.warning(self.toolbar, '删除歌曲', '删除失败！')
        else:
            QMessageBox.information(self.toolbar, '删除歌曲', '删除成功！')
        return ok

    def _upload_song(self):
        path, _ = QFileDialog.getOpenFileName(self.toolbar, '选择文件', Path.home().as_posix(),
                                              'Supported Files (*.mp3 *.m4a, *.wma, *.flac, *.ogg);; All Files (*.*)')
        if path == '':
            return
        ok = self._provider.upload_song(path)
        if not ok:
            QMessageBox.warning(self.toolbar, '上传音乐', '上传失败！')
        else:
            QMessageBox.information(self.toolbar, '上传音乐', '上传成功！')

    def show_by_tab_id(self, tab_id):
        query = {'tab_id': tab_id.value}
        self._app.browser.goto(page='/providers/ytmusic/more', query=query)

    def render_tabbar(self):
        super().render_tabbar()
        try:
            self.tabbar.songs_btn.setText('上传的歌曲')
            self.tabbar.albums_btn.setText('上传的专辑')
            self.tabbar.artists_btn.setText('上传的艺术家')
            self.tabbar.videos_btn.hide()
            self.tabbar.playlists_btn.hide()
        except Exception as e:
            logger.warning(str(e))
