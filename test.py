from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.provider import provider

provider.setup_http_proxy("http://127.0.0.1:7890")


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


def test_switch_profile():
    profile_name = None
    gaia_id = None
    if not (profile_name or gaia_id):
        print("No profile switch requested.")
        return
    print("Switching profile:", profile_name if profile_name else gaia_id)
    user = provider.switch_profile(account_name=profile_name, gaia_id=gaia_id)
    print("UserModel after switch:", user)


def test_all():
    test_current_user()
    test_list_profiles()
    test_switch_profile()


if __name__ == "__main__":
    test_all()
