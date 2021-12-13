import asyncio
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtProperty, pyqtSlot, pyqtSignal
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget

from fuo_ytmusic import YtmusicProvider
from fuo_ytmusic.models import YtmusicPlaylistModel


class ExploreBackend(QObject):
    categoriesLoaded = pyqtSignal('QVariantMap')
    playlistsLoaded = pyqtSignal('QVariantList')

    def __init__(self, provider: YtmusicProvider, app):
        super().__init__()
        self._provider = provider
        self._app = app

    async def categories(self):
        loop = asyncio.get_event_loop()
        categories = await loop.run_in_executor(None, self._provider.categories)
        result = dict()
        result['forYou'] = [{'title': c.title, 'params': c.params} for c in categories.forYou]
        result['moods'] = [{'title': c.title, 'params': c.params} for c in categories.moods]
        result['genres'] = [{'title': c.title, 'params': c.params} for c in categories.genres]
        self.categoriesLoaded.emit(result)

    async def playlists(self, params: str):
        loop = asyncio.get_event_loop()
        playlists = await loop.run_in_executor(None, self._provider.service.category_playlists, params)
        result = [{'id': p.playlistId, 'name': p.title, 'cover': p.cover} for p in playlists]
        self.playlistsLoaded.emit(result)

    @pyqtSlot()
    def load_categories(self):
        asyncio.ensure_future(self.categories())

    @pyqtSlot(str)
    def load_playlists(self, params: str):
        asyncio.ensure_future(self.playlists(params))

    @pyqtSlot(str, str, str)
    def goto_playlist(self, playlist_id: str, name: str, cover: str):
        model = YtmusicPlaylistModel(identifier=playlist_id, source='ytmusic', name=name, cover=cover)
        self._app.browser.goto(model=model)

    @pyqtProperty(bool, constant=True)
    def is_dark(self) -> bool:
        return self._app.config.THEME == 'dark'


async def render(req, **_):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
    os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'
    view = QQuickView()
    app._ytmusic_explore_backend = ExploreBackend(provider, app)
    # noinspection PyProtectedMember
    view.rootContext().setContextProperty('explore_backend', app._ytmusic_explore_backend)
    container = QWidget.createWindowContainer(view, app.ui.right_panel)
    container.setFocusPolicy(Qt.TabFocus)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'page_explore.qml').as_posix()))
    app.ui.right_panel.set_body(container)
