from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtProperty
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QWidget

from fuo_ytmusic import YtmusicProvider


class ExploreBackend(QObject):
    def __init__(self, provider: YtmusicProvider):
        super().__init__()
        self._provider = provider

    @pyqtProperty('QVariantMap', constant=True)
    def categories(self) -> dict:
        result = dict()
        categories = self._provider.categories()
        result['forYou'] = [{'title': c.title, 'params': c.params} for c in categories.forYou]
        result['moods'] = [{'title': c.title, 'params': c.params} for c in categories.moods]
        result['genres'] = [{'title': c.title, 'params': c.params} for c in categories.genres]
        return result


async def render(req, **_):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
    view = QQuickView()
    app._ytmusic_explore_backend = ExploreBackend(provider)
    # noinspection PyProtectedMember
    view.rootContext().setContextProperty('explore_backend', app._ytmusic_explore_backend)
    container = QWidget.createWindowContainer(view, app.ui.right_panel)
    container.setFocusPolicy(Qt.TabFocus)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile((Path(__file__).parent / 'qml' / 'page_explore.qml').as_posix()))
    app.ui.right_panel.set_body(container)
