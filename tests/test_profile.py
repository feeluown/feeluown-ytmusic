import json
from pathlib import Path

from fuo_ytmusic.profile import YtmusicProfileManager


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DummyApi:
    def __init__(self, menu_response=None):
        self.menu_response = menu_response or {}
        self.on_behalf_of_user = None
        self.check_auth_called = False

    def check_auth(self):
        self.check_auth_called = True

    def set_on_behalf_of_user(self, gaia_id):
        self.on_behalf_of_user = gaia_id

    def send_api_request(self, _endpoint, _body):
        return self.menu_response


class DummyService:
    def __init__(self, menu_response=None):
        self.api = DummyApi(menu_response=menu_response)


def load_fixture(name):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_list_profiles_filters_missing_handle(monkeypatch):
    switcher = load_fixture("account_switcher.json")
    service = DummyService()
    manager = YtmusicProfileManager(service)
    monkeypatch.setattr(manager, "_get_account_switcher", lambda: switcher)

    profiles = manager.list_profiles()
    names = [p["accountName"] for p in profiles]
    assert any("@" in p["channelHandle"] for p in profiles)
    assert all(name for name in names)
    selected = [p for p in profiles if p["isSelected"]]
    assert len(selected) == 1


def test_get_current_account_info_uses_menu_channel(monkeypatch):
    switcher = load_fixture("account_switcher.json")
    menu = load_fixture("account_menu.json")
    service = DummyService(menu_response=menu)
    manager = YtmusicProfileManager(service)
    monkeypatch.setattr(manager, "_get_account_switcher", lambda: switcher)

    info = manager.get_current_account_info()
    assert info["accountName"]
    assert info["gaiaId"]
    assert info["channelId"]
    assert service.api.check_auth_called is True


def test_switch_profile_by_name_sets_on_behalf(monkeypatch):
    switcher = load_fixture("account_switcher.json")
    menu = load_fixture("account_menu.json")
    service = DummyService(menu_response=menu)
    manager = YtmusicProfileManager(service)
    monkeypatch.setattr(manager, "_get_account_switcher", lambda: switcher)

    profiles = manager.list_profiles()
    assert profiles
    info = manager.switch_profile(account_name=profiles[0]["accountName"])
    assert info["accountName"]
    assert info["channelId"]
    assert service.api.on_behalf_of_user
