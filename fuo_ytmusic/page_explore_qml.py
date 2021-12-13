import asyncio
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtProperty, pyqtSlot, pyqtSignal
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget

from fuo_ytmusic import YtmusicProvider
from fuo_ytmusic.models import YtmusicPlaylistModel


from feeluown.gui.base_renderer import TabBarRendererMixin


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
        if categories.forYou:
            result['forYou'] = [{'title': c.title, 'params': c.params} for c in categories.forYou]
        result['moods'] = [{'title': c.title, 'params': c.params} for c in categories.moods]
        result['genres'] = [{'title': c.title, 'params': c.params} for c in categories.genres]
        return result

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
        
    tab_index = int(req.query.get('tab_index', 0))
    backend = ExploreBackend(provider, app)
    categories = await backend.categories()
    renderer = ExploreRenderer(app, tab_index, categories, backend)
    await renderer.render()


class ExploreRenderer(TabBarRendererMixin):

    def __init__(self, app, tab_index, categories, backend):
        self._app = app
        app._xx_renderer = self
        self._ytmusic_explore_backend = backend

        # Initialize tabs.
        self.tabs = []
        flows = ['forYou', 'moods', 'genres']
        for key, data in categories.items():
            flow_index = flows.index(key)
            self.tabs.append((key, flow_index))
        for key, flow_index in self.tabs:
            if flow_index == tab_index:
                real_tab_index = flow_index
                tab_data = categories[key]
                break
        else:
            key, flow_index = self.tabs[0]
            real_tab_index = flow_index
            tab_data = categories[key]

        self.tab_index = real_tab_index
        self.tab_data = tab_data

    async def render(self):
        self.render_tab_bar()

        os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'
        view = QQuickView()
        view.rootContext().setContextProperty('explore_backend', self._ytmusic_explore_backend)
        view.rootContext().setContextProperty('flow_index', self.tab_index)
        # HELP: I don't know how to pass tab_data to qml. 
        self._ytmusic_explore_backend._tab_data = self.tab_data
        # view.rootContext().setContextProperty('flow_data', Model([self.tab_data]))
        container = QWidget.createWindowContainer(view, self._app.ui.right_panel)
        container.setFocusPolicy(Qt.TabFocus)
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'page_explore.qml').as_posix()))
        
        self._app.ui.right_panel.set_body(container)

    def render_by_tab_index(self, tab_index):
        self._app.browser.goto(page='/providers/ytmusic/explore',
                               query={'tab_index': tab_index})
