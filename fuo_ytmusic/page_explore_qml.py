import asyncio
from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QPoint, QSize, QMargins, QUrl, QObject, pyqtProperty
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QButtonGroup, QPushButton, QSizePolicy, QLayout, \
    QTabWidget, QAbstractButton
from feeluown.gui.helpers import BgTransparentMixin, fetch_cover_wrapper
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, PlaylistFilterProxyModel
from feeluown.utils.reader import wrap

from fuo_ytmusic import YtmusicProvider
from fuo_ytmusic.helpers import Singleton
from fuo_ytmusic.models import Categories


class ExploreBackend(QObject):
    def __init__(self, provider: YtmusicProvider):
        super().__init__()
        self._provider = provider

    @pyqtProperty(bool, constant=True)
    def categories(self) -> Categories:
        return self._provider.categories()


async def render(req, **_):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
    view = QQuickView()
    view.rootContext().setContextProperty('explore_backend', ExploreBackend(provider))
    container = QWidget.createWindowContainer(view, app.ui.right_panel)
    container.setFocusPolicy(Qt.TabFocus)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'page_explore.qml').as_posix()))

    # async def select_playlist(btn: QAbstractButton):
    #     params: str = btn.property('params')
    #     loop = asyncio.get_event_loop()
    #     playlists = await loop.run_in_executor(None, provider.category_playlists, params)
    #     model = PlaylistListModel(wrap(playlists),
    #                               fetch_cover_wrapper(app.img_mgr),
    #                               {p.identifier: p.name for p in app.library.list()})
    #     filter_model = PlaylistFilterProxyModel()
    #     filter_model.setSourceModel(model)
    #     view.playlist_list_view.setModel(filter_model)

    # view.recommand_view.button_group.buttonPressed.connect(lambda _: asyncio.ensure_future(select_playlist(_)))

    # view.playlist_list_view.show_playlist_needed.connect(
    #     lambda model: app.browser.goto(model=model))
    app.ui.right_panel.set_body(container)
