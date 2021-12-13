import asyncio
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtProperty, pyqtSlot, pyqtSignal
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget

from feeluown.gui.base_renderer import TabBarRendererMixin
from fuo_ytmusic import YtmusicProvider
from fuo_ytmusic.models import YtmusicPlaylistModel


class ExploreBackend(QObject):
    categoriesLoaded = pyqtSignal('QVariantMap')
    hacked = pyqtSignal('QVariantMap')
    playlistsLoaded = pyqtSignal('QVariantList')

    def __init__(self, provider: YtmusicProvider, app):
        super().__init__()
        self._provider = provider
        self._app = app
        self._categories = {}

    async def categories(self):
        loop = asyncio.get_event_loop()
        categories = await loop.run_in_executor(None, self._provider.categories)
        result = dict()
        if categories.forYou:
            result['forYou'] = [{'title': c.title, 'params': c.params} for c in categories.forYou]
        result['moods'] = [{'title': c.title, 'params': c.params} for c in categories.moods]
        result['genres'] = [{'title': c.title, 'params': c.params} for c in categories.genres]
        # HACK: store result as _categories so that we can emit it in hacked signal.
        self._categories = result
        return result

    @pyqtSlot()
    def hack(self):
        # HELP: Don't know how to pass the data to QML. This method is called by
        # QML object and the QML object listen to the hacked signal to get the categories data.
        self.hacked.emit(self._categories)

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
        return self._app.theme_mgr.theme == 'dark'


async def render(req, **_):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
        
    flow_index = int(req.query.get('flow_index', 0))
    backend = ExploreBackend(provider, app)
    categories = await backend.categories()

    # `tabs` refers to tabs in Tabbar and `flows` refers to flow in QML.
    tabs = []
    tab_index: int = None  # Value is assigned lator.
    flows = ['forYou', 'moods', 'genres']
    # Calculate the right flow_index index because the flow_index passed in can be invalid.
    # For example, flow_index is 0 by default. When forYou has no data, the flow_index
    # should be changed into another.
    while flows[flow_index] not in categories:
        flow_index = (flow_index + 1) % 3
    for key, _ in categories.items():
        tabs.append((key, flows.index(key)))
    for i, (_, tab_flow_index) in enumerate(tabs):
        if flow_index == tab_flow_index:
            tab_index = i
            break
    assert tab_index is not None
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
