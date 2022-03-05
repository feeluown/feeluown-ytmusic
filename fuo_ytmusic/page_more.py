import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Optional, List

from PyQt5.QtCore import QObject, QUrl, pyqtSlot, QVariant, Qt, QModelIndex, QAbstractTableModel, pyqtProperty
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from feeluown.gui.widgets import TextButton
from feeluown.gui.widgets.songs import SongsTableView
from feeluown.utils import aio
from feeluown.gui.base_renderer import LibraryTabRendererMixin
from feeluown.gui.page_containers.table import Renderer
from feeluown.gui.widgets.tabbar import Tab

from fuo_ytmusic import YtmusicProvider

logger = logging.getLogger(__name__)


class UploadingSongListModel(QAbstractTableModel):
    def __init__(self, header: List[str], data: list):
        self._header = header
        self._data = data
        super(UploadingSongListModel, self).__init__()

    def update_state(self, index: int, state: bool):
        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(self.index(index, 0), self.index(index, len(self._header) - 1))
        self._data[index][1] = '上传成功' if state else '上传失败'

    def insert_data(self, new_data: list):
        last_index = self.rowCount()
        self.beginInsertRows(QModelIndex(), last_index, last_index + len(new_data) - 1)
        self._data.extend(new_data)
        self.endInsertRows()

    def clear_data(self):
        self.beginRemoveRows(QModelIndex(), 0, self.rowCount() - 1)
        self._data.clear()
        self.endRemoveRows()

    def get_data(self):
        return self._data

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = None):
        if role == Qt.DisplayRole:
            return self._header[section]

    def data(self, index: QModelIndex, role: int = None):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self._header)


class UploaderBackend(QObject):
    def __init__(self, provider: YtmusicProvider = None):
        super(UploaderBackend, self).__init__()
        self._provider = provider
        self._upload_thread: Optional[threading.Thread] = None
        self._thread_paused = False
        self._uploading_song_model = UploadingSongListModel(['文件路径', '上传状态'], [])

    @pyqtProperty(UploadingSongListModel, constant=True)
    def uploading_song_model(self) -> UploadingSongListModel:
        return self._uploading_song_model

    @pyqtSlot(name='clearAll')
    def clear_all(self):
        self._uploading_song_model.clear_data()

    def _update_upload_state(self, index: int, state: bool):
        self._uploading_song_model.update_state(index, state)

    def _upload(self):
        for i, song in enumerate(self._uploading_song_model.get_data()):
            file = Path(song[0])
            if not file.exists():
                continue
            state = self._provider.upload_song(file.as_posix())
            self._update_upload_state(i, state)
            while self._thread_paused:
                time.sleep(1)
        self._upload_thread = None

    def __del__(self):
        if self._upload_thread is not None:
            del self._upload_thread
            self._upload_thread = None

    @pyqtProperty(str, constant=True)
    def is_uploading(self) -> str:
        if self._upload_thread is None:
            return '上传'
        elif self._thread_paused:
            return '继续'
        else:
            return '暂停'

    @pyqtSlot()
    def upload(self):
        if self._upload_thread is not None:
            self._thread_paused = False
            return
        self._upload_thread = threading.Thread(target=self._upload)
        self._upload_thread.start()

    @pyqtSlot()
    def pause(self):
        if self._upload_thread is not None:
            return
        self._thread_paused = True

    @pyqtSlot(QVariant, name='filesDropped')
    def files_dropped(self, value: QVariant) -> bool:
        if len(value) == 0:
            return False
        files_data = []
        # noinspection PyTypeChecker
        for url in value:
            url: QUrl
            path = Path(url.toLocalFile())
            if path.is_file():
                files_data.append([path.as_posix(), '待上传'])
            elif path.is_dir():
                # 支持的文件类型 *.mp3 *.m4a, *.wma, *.flac, *.ogg
                extensions = ['*.mp3', '*.m4a', '*.wma', '*.flac', '*.ogg', '*.MP3', '*.M4A', '*.WMA', '*.FLAC', '*.OGG']
                for e_ in extensions:
                    p_ = path.rglob(e_)
                    for p in p_:
                        files_data.append([p.as_posix(), '待上传'])
        if len(files_data) == 0:
            return False
        self._uploading_song_model.insert_data(files_data)
        return True


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
        self._backend = UploaderBackend(provider)
        self._uploader: Optional[QQuickView] = None
        self._load_uploader()

    def _load_uploader(self):
        self._uploader = QQuickView()
        self._uploader.setTitle('上传音乐')
        self._uploader.rootContext().setContextProperty('backend', self._backend)
        self._uploader.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'uploader.qml').as_posix()))
        self._uploader.setResizeMode(QQuickView.SizeRootObjectToView)

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
            btn.clicked.connect(self._show_uploader)
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

    def _show_uploader(self):
        self._uploader.show()

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
