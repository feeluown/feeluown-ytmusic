import logging
import json
from pathlib import Path

from feeluown.gui.provider_ui import AbstractProviderUi
from feeluown.app.gui_app import GuiApp
from feeluown.gui.widgets.login import LoginDialog as LoginDialog_
from feeluown.utils import aio
from feeluown.utils.dispatch import Signal

from fuo_ytmusic.qt_compat import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFormLayout,
    TextSelectableByMouse,
    Dialog,
)
from fuo_ytmusic.provider import provider
from fuo_ytmusic.consts import HEADER_FILE

logger = logging.getLogger(__name__)


class ProviderUI(AbstractProviderUi):
    def __init__(self, app: GuiApp):
        self._app = app
        self._login_event = Signal()

    @property
    def provider(self):
        return provider

    def get_colorful_svg(self) -> str:
        return (Path(__file__).parent / "assets" / "icon.svg").as_posix()

    def login_or_go_home(self):
        if not provider.has_current_user():
            self._dialog = LoginDialog(self.provider)
            self._dialog.login_succeed.connect(self.on_login_succeed)
            self._dialog.show()
        else:
            logger.info("already logged in")
            self.login_event.emit(self, 2)

    @property
    def login_event(self):
        return self._login_event

    def on_login_succeed(self):
        del self._dialog
        self.login_event.emit(self, 1)


class LoginDialog(LoginDialog_):
    def __init__(self, provider):
        super().__init__()

        self._provider = provider

        self._login_btn = QPushButton("登录")
        self.__hint_label = QLabel(
            "欢迎来到 Youtube Music 登录界面 :)\n\n"
            "登录 Youtube Music 虽然繁琐，但一劳‘永逸’（因为认证信息的过期时间很长）。"
            "当然，不登录也可以使用 Youtube Music 的大部分功能，比如搜索、播放等。"
            "登录请按照下述指南操作：\n\n"
            "在浏览器中登录 Youtube Music，打开“开发者工具”，"
            "点击‘媒体库’按钮（这样会触发一个 POST 请求，这个请求通常会携带必要的认证信息），"
            "拷贝这个 HTTP 请求的 Authorization 和 Cookie 字段值并填入到表格中，点击登录按钮。"
        )
        self.__progress_label = QLabel()
        self.__input_auth_header = QLineEdit()
        self.__input_cookies = QLineEdit()
        self.__hint_label.setTextInteractionFlags(TextSelectableByMouse)
        self.__hint_label.setWordWrap(True)
        self.__progress_label.setWordWrap(True)
        self.setup_ui()

        aio.run_afn_ref(self.try_auto_login)

    def setup_ui(self):
        self.setWindowFlags(self.windowFlags() | Dialog)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.__input_auth_header.setPlaceholderText(
            "类似：SAPISIDHASH 1765595295_abcd_u SAPISID1PHASH ..."
        )
        self.__input_cookies.setPlaceholderText("请复制完整的值")
        form_layout.addRow("Authorization:", self.__input_auth_header)
        form_layout.addRow("Cookie:", self.__input_cookies)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.__hint_label)
        self._layout.addLayout(form_layout)
        self._layout.addWidget(self.__progress_label)
        self._layout.addWidget(self._login_btn)

        self._login_btn.clicked.connect(lambda: aio.run_afn_ref(self.login))

    def generate_header_file(self, auth: str, cookie: str):
        tpl = {
            "Accept": "*/*",
            "Authorization": auth,
            "Content-Type": "application/json",
            "X-Goog-AuthUser": "0",
            "x-origin": "https://music.youtube.com",
            "Cookie": cookie,
        }
        with HEADER_FILE.open("w") as f:
            json.dump(tpl, f, indent=2)

    async def login(self):
        auth = self.__input_auth_header.text()
        cookie = self.__input_cookies.text()
        if not (auth and cookie):
            self.show_progress("请输入 Authorization 和 Cookie", color="red")
            return
        self.generate_header_file(auth, cookie)
        self.show_progress("尝试登录...", color="green")
        await self.try_login()

    async def try_auto_login(self):
        if HEADER_FILE.exists():
            self.show_progress("发现已存在的认证信息，尝试登录...", color="blue")
            await self.try_login()
        else:
            self.show_progress("等待用户填充认证信息...", color="blue")

    async def try_login(self):
        try:
            user = await aio.run_fn(self._provider.try_get_user_with_headerfile)
        except Exception as e:
            self.show_progress(f"登录失败：{e}", color="red")
            return

        if user is None:
            self.show_progress("登录失败，可能是认证信息无效。", color="red")
            return
        self.show_progress(f"登录成功，用户：{user.name}", color="green")
        self._provider.auth(user)
        self.login_succeed.emit()
        self.hide()

    def show_progress(self, text, color="black"):
        if color is None:
            color = ""
        self.__progress_label.setText(f"<p style='color: {color}'>{text}</p>")


if __name__ == "__main__":
    from feeluown.gui.debug import async_simple_qapp

    with async_simple_qapp():
        dialog = LoginDialog(provider)
        dialog.show()
