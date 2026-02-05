"""Manual test for YouTube Music profile listing/switching."""

import pytest
from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.provider import provider


@pytest.mark.manual
def test_list_profiles():
    if not HEADER_FILE.exists():
        print(f"Header file not found: {HEADER_FILE}")
        return
    try:
        provider.service.reinitialize_by_headerfile(HEADER_FILE)
    except Exception as e:
        print(f"Failed to initialize service for profiles: {e}")
        return
    profiles = provider.list_profiles()
    print("Profiles:", profiles)

@pytest.mark.manual
def test_current_user():
    if not HEADER_FILE.exists():
        print(f"Header file not found: {HEADER_FILE}")
        return
    try:
        user = provider.try_get_user_with_headerfile()
    except Exception as e:
        print(f"Failed to fetch user info from header file: {e}")
        return
    if user is None:
        print("Failed to fetch user info from header file.")
        return
    print("UserModel:", user)
    info = provider.service.get_current_account_info()
    print("Account info:", info)

@pytest.mark.manual
def test_auto_login_and_playlists():
    if not HEADER_FILE.exists():
        print(f"Header file not found: {HEADER_FILE}")
        return
    try:
        provider.service.reinitialize_by_headerfile(HEADER_FILE)
    except Exception as e:
        print(f"Failed to initialize service for profiles: {e}")
        return
    provider.auto_login()
    if not provider.has_current_user():
        print("Auto login failed: no current user")
        return
    user = provider.get_current_user()
    print("Auto login user:", user)
    try:
        playlists = provider.current_user_list_playlists()
    except Exception as e:
        print(f"Failed to fetch playlists after auto login: {e}")
        return
    print(f"Playlists count: {len(playlists)}")


@pytest.mark.manual
def test_switch_profile():
    profile_name = None
    gaia_id = None
    if not (profile_name or gaia_id):
        print("No profile switch requested.")
        return
    print("Switching profile:", profile_name if profile_name else gaia_id)
    user = provider.switch_profile(account_name=profile_name, gaia_id=gaia_id)
    print("UserModel after switch:", user)


@pytest.mark.manual
def test_all():
    test_current_user()
    test_list_profiles()
    test_switch_profile()
    test_auto_login_and_playlists()
