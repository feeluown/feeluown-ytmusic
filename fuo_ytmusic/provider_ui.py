import logging
from pathlib import Path

from feeluown.app.gui_app import GuiApp
from feeluown.gui.provider_ui import AbstractProviderUi
from feeluown.gui.widgets.login import LoginDialog as LoginDialog_
from feeluown.utils import aio
from feeluown.utils.dispatch import Signal

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.headerfile import write_headerfile
from fuo_ytmusic.provider import provider
from fuo_ytmusic.qt_compat import (
    Dialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    TextSelectableByMouse,
)

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

    def context_menu_add_items(self, menu):
        action = menu.addAction("Switch account")
        action.triggered.connect(lambda: aio.run_afn_ref(self.switch_profile_dialog))

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

    async def switch_profile_dialog(self):
        if not provider.has_current_user():
            self._app.show_msg("Please log in before switching accounts.")
            return
        try:
            profiles = await aio.run_fn(provider.list_profiles)
        except Exception as e:
            self._app.show_msg(f"Failed to fetch account list: {e}")
            return
        if not profiles:
            self._app.show_msg("No available accounts found.")
            return

        items = []
        mapping = {}
        for profile in profiles:
            name = profile.get("accountName") or "Unknown"
            handle = profile.get("channelHandle")
            display = f"{name} ({handle})" if handle else name
            items.append(display)
            mapping[display] = profile

        selected, ok = QInputDialog.getItem(
            self._app,
            "Switch account",
            "Select an account",
            items,
            0,
            False,
        )
        if not ok or not selected:
            return
        profile = mapping.get(selected)
        if not profile:
            return
        try:
            await aio.run_fn(provider.switch_profile, profile.get("accountName"))
        except Exception as e:
            self._app.show_msg(f"Failed to switch account: {e}")
            return
        self._app.show_msg(f"Switched to: {profile.get('accountName')}")
        # Notify UI to refresh current user data/playlists.
        self.login_event.emit(self, 2)


class LoginDialog(LoginDialog_):
    def __init__(self, provider):
        super().__init__()

        self._provider = provider

        self._login_btn = QPushButton("Login")
        self.__hint_label = QLabel(
            "Welcome to the YouTube Music sign-in dialog.\n\n"
            "1) Sign in on music.youtube.com in your browser.\n"
            "2) Open DevTools and trigger a request from Library.\n"
            "3) Copy Authorization and Cookie from that HTTP request.\n"
            "4) Paste them into the fields below, then click Login."
        )
        self.__progress_label = QLabel()
        self.__input_auth_header = QLineEdit()
        self.__input_cookies = QLineEdit()
        self.__hint_label.setTextInteractionFlags(TextSelectableByMouse)
        # Allow users to copy both onboarding hints and runtime status messages.
        self.__progress_label.setTextInteractionFlags(TextSelectableByMouse)
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
            "Example: SAPISIDHASH 1765595295_abcd_u SAPISID1PHASH ..."
        )
        self.__input_cookies.setPlaceholderText("Paste the full cookie value")
        form_layout.addRow("Authorization:", self.__input_auth_header)
        form_layout.addRow("Cookie:", self.__input_cookies)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.__hint_label)
        self._layout.addLayout(form_layout)
        self._layout.addWidget(self.__progress_label)
        self._layout.addWidget(self._login_btn)

        self._login_btn.clicked.connect(lambda: aio.run_afn_ref(self.login))

    def generate_header_file(self, auth: str, cookie: str):
        write_headerfile(auth, cookie, HEADER_FILE)

    async def login(self):
        auth = self.__input_auth_header.text()
        cookie = self.__input_cookies.text()
        if not (auth and cookie):
            self.show_progress("Please input Authorization and Cookie.", color="red")
            return
        self.generate_header_file(auth, cookie)
        self.show_progress("Trying to sign in...", color="green")
        await self.try_login()

    async def try_auto_login(self):
        if HEADER_FILE.exists():
            self.show_progress(
                "Found existing credentials, trying to sign in...",
                color="blue",
            )
            await self.try_login()
        else:
            self.show_progress("Waiting for credentials...", color="blue")

    async def try_login(self):
        try:
            user = await aio.run_fn(self._provider.try_get_user_with_headerfile)
        except Exception as e:
            self.show_progress(f"Sign-in failed: {e}", color="red")
            return

        if user is None:
            self.show_progress(
                "Sign-in failed: credentials may be invalid.",
                color="red",
            )
            return
        self.show_progress(f"Signed in as: {user.name}", color="green")
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
