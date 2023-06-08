import asyncio
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtProperty, pyqtSlot, pyqtSignal
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget

from feeluown.library import BriefPlaylistModel
from feeluown.gui.base_renderer import TabBarRendererMixin
from fuo_ytmusic import YtmusicProvider


class ExploreBackend(QObject):
    categoriesLoaded = pyqtSignal('QVariantList')
    playlistsLoaded = pyqtSignal('QVariantList')

    def __init__(self, provider: YtmusicProvider, app):
        super().__init__()
        self._provider = provider
        self._app = app

    async def categories(self):
        loop = asyncio.get_event_loop()
        categories = await loop.run_in_executor(None, self._provider.categories)
        result = [{'key': category.key,
                   'value': [{'title': playlist.title, 'params': playlist.params} for playlist in category.value]} for
                  category in categories]
        self.categoriesLoaded.emit(result)
        return categories

    async def playlists(self, params: str):
        loop = asyncio.get_event_loop()
        playlists = await loop.run_in_executor(None, self._provider.service.category_playlists, params)
        result = [{'id': p.playlistId, 'name': p.title, 'cover': p.thumbnail} for p in playlists]
        self.playlistsLoaded.emit(result)

    @pyqtSlot()
    def load_categories(self):
        asyncio.ensure_future(self.categories())

    @pyqtSlot(str)
    def load_playlists(self, params: str):
        asyncio.ensure_future(self.playlists(params))

    @pyqtSlot(str, str, str)
    def goto_playlist(self, playlist_id: str, name: str, cover: str):
        model = BriefPlaylistModel(identifier=playlist_id, source='ytmusic', name=name)
        self._app.browser.goto(model=model)

    @pyqtProperty(bool, constant=True)
    def is_dark(self) -> bool:
        return self._app.theme_mgr.theme == 'dark'


async def render(req, **_):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
    backend = ExploreBackend(provider, app)
    categories = await backend.categories()
    tab_index: int = int(req.query.get('flow_index', 0))
    tabs = [(c.key, i) for i, c in enumerate(categories)]
    renderer = ExploreRenderer(app, tab_index, tabs, backend)
    await renderer.render()
    backend._x_renderer = renderer  # HACK: prevent renderer objec to be freed.


class ExploreRenderer(TabBarRendererMixin):

    def __init__(self, app, tab_index, tabs, backend):
        self._app = app
        self._backend = backend
        self.tab_index = tab_index
        self.tabs = tabs

    async def render(self):
        self.render_tab_bar()

        os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'
        view = QQuickView()
        view.rootContext().setContextProperty('explore_backend', self._backend)
        view.rootContext().setContextProperty('flow_index', self.get_flow_index(self.tab_index))
        container = QWidget.createWindowContainer(view, self._app.ui.right_panel)
        container.setFocusPolicy(Qt.TabFocus)
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'page_explore.qml').as_posix()))
        self._app.ui.right_panel.set_body(container)

    def render_by_tab_index(self, tab_index):
        self._app.browser.goto(page='/providers/ytmusic/explore',
                               query={'flow_index': self.get_flow_index(tab_index)})

    def get_flow_index(self, tab_index):
        return self.tabs[tab_index][1]
