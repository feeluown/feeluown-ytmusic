from PyQt5.QtCore import Qt, QRect, QPoint, QSize, QMargins
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QButtonGroup, QPushButton, QHBoxLayout, QSizePolicy, QLayout, \
    QTabWidget
from feeluown.gui.helpers import BgTransparentMixin
from feeluown.gui.widgets.playlist import PlaylistListView

from fuo_ytmusic import YtmusicProvider


async def render(req, **kwargs):
    app = req.ctx['app']
    provider = app.library.get('ytmusic')
    view = ExploreView(provider)
    # model = PlaylistListModel(wrap(playlists),
    #                           fetch_cover_wrapper(app.img_mgr),
    #                           {p.identifier: p.name for p in app.library.list()})
    # filter_model = PlaylistFilterProxyModel()
    # filter_model.setSourceModel(model)
    # view.playlist_list_view.setModel(filter_model)
    # view.playlist_list_view.show_playlist_needed.connect(
    #     lambda model: app.browser.goto(model=model))
    app.ui.right_panel.set_body(view)


class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.take_at(0)
        while item:
            item = self.take_at(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if index >= 0 and index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(),
                      2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Horizontal)
            layout_spacing_y = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Vertical)
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class HeaderLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('HeaderLabel {color: #666666;}')
        self.setTextFormat(Qt.RichText)


class _PlaylistListView(PlaylistListView, BgTransparentMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, no_scroll_v=True, **kwargs)
        BgTransparentMixin.__init__(self)


class SelectorButton(QPushButton):
    def __init__(self, text):
        super(SelectorButton, self).__init__()
        self.setStyleSheet('SelectorButton { border-radius: 2px; background: #cfcfcf; padding: 10px 20px; }'
                           'SelectorButton:checked { background: #4ab7ff; }')
        self.setFixedHeight(30)
        self.setText(text)
        self.setFlat(True)
        self.setCheckable(True)


class RecommendView(QWidget):
    def __init__(self, provider):
        super(RecommendView, self).__init__()
        self.provider: YtmusicProvider = provider
        self._layout = QVBoxLayout(self)
        self.button_group = QButtonGroup()

        self.button_layout_1 = FlowLayout()
        button_widget_1 = QWidget()
        button_widget_1.setLayout(self.button_layout_1)
        self.button_layout_2 = FlowLayout()
        button_widget_2 = QWidget()
        button_widget_2.setLayout(self.button_layout_2)
        self.button_layout_3 = FlowLayout()
        button_widget_3 = QWidget()
        button_widget_3.setLayout(self.button_layout_3)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(button_widget_1, '为你推荐')
        self.tab_widget.addTab(button_widget_2, '心情')
        self.tab_widget.addTab(button_widget_3, '流派')

        self.setup_categories()
        self._layout.addWidget(self.tab_widget)

        self.tab_widget.currentChanged.connect(self.update_sizes)
        self.update_sizes(0)

    def update_sizes(self, _):
        for i in range(self.tab_widget.count()):
            self.tab_widget.widget(i).setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        current = self.tab_widget.currentWidget()
        current.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def setup_categories(self):
        categories = self.provider.categories()
        for c in categories.forYou:
            btn = SelectorButton(c.title)
            self.button_group.addButton(btn)
            self.button_layout_1.addWidget(btn)
        for c in categories.moods:
            btn = SelectorButton(c.title)
            self.button_group.addButton(btn)
            self.button_layout_2.addWidget(btn)
        for c in categories.genres:
            btn = SelectorButton(c.title)
            self.button_group.addButton(btn)
            self.button_layout_3.addWidget(btn)


class ExploreView(QWidget):
    def __init__(self, provider):
        super().__init__(parent=None)

        self.header_title = HeaderLabel()
        self.header_playlist_list = HeaderLabel()
        # self.header_daily_rec = HeaderLabel()
        # self.playlist_list_view = _PlaylistListView(img_min_width=100)
        # self.daily_rec_btn = TextButton('查看每日推荐')

        self.header_title.setText('<h1>发现</h1>')
        self.header_playlist_list.setText('<h2>个性化推荐</h2>')
        # self.header_daily_rec.setText('<h2>每日推荐</h2>')
        self.recommand_view = RecommendView(provider)

        # self._daily_rec_layout = QHBoxLayout()
        self._layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        self._layout.setContentsMargins(0, 10, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.header_title)
        self._layout.addSpacing(30)
        # self._layout.addWidget(self.header_daily_rec)
        # self._layout.addSpacing(5)
        # self._layout.addLayout(self._daily_rec_layout)
        # self._layout.addSpacing(20)
        self._layout.addWidget(self.header_playlist_list)
        self._layout.addStretch(0)
        self._layout.addSpacing(10)
        self._layout.addWidget(self.recommand_view)
        self._layout.addStretch(1)
        # self._daily_rec_layout.addSpacing(25)
        # self._daily_rec_layout.addWidget(self.daily_rec_btn)
        # self._daily_rec_layout.addStretch(0)
