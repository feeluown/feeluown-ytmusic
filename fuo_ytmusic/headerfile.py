import json
from typing import Optional

from fuo_ytmusic.consts import HEADER_FILE

# Store selected profile in headerfile using a custom key; this is not part of
# YouTube headers but lets us persist profile selection without extra files.
PROFILE_GAIA_KEY = "X-Feeluown-Profile-Gaia-Id"


def write_headerfile(auth: str, cookie: str, headerfile_path=HEADER_FILE) -> None:
    tpl = {
        "Accept": "*/*",
        "Authorization": auth,
        "Content-Type": "application/json",
        "X-Goog-AuthUser": "0",
        "x-origin": "https://music.youtube.com",
        "Cookie": cookie,
    }
    with headerfile_path.open("w") as handle:
        json.dump(tpl, handle, indent=2, ensure_ascii=True)


def read_headerfile(headerfile_path=HEADER_FILE) -> dict:
    if headerfile_path is None:
        return {}
    try:
        if headerfile_path.exists():
            with open(headerfile_path, "r") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def strip_profile_meta(headers: dict) -> dict:
    if not headers:
        return {}
    # Ensure our custom profile marker isn't forwarded as a real request header.
    data = dict(headers)
    data.pop(PROFILE_GAIA_KEY, None)
    return data


def get_profile_gaia_id(headerfile_path=HEADER_FILE) -> Optional[str]:
    # Read persisted profile selection from headerfile (if any).
    data = read_headerfile(headerfile_path)
    return data.get(PROFILE_GAIA_KEY)


def update_profile_gaia_id(
    gaia_id: Optional[str], headerfile_path=HEADER_FILE
) -> bool:
    if headerfile_path is None:
        return False
    # Persist/clear selected profile in headerfile so it survives app restarts.
    data = read_headerfile(headerfile_path)
    original = data.get(PROFILE_GAIA_KEY)
    if gaia_id:
        data[PROFILE_GAIA_KEY] = gaia_id
    else:
        data.pop(PROFILE_GAIA_KEY, None)
    if data.get(PROFILE_GAIA_KEY) == original:
        return False
    with open(headerfile_path, "w") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
    return True


def update_headerfile_cookie(
    cookie_value: str, headerfile_path=HEADER_FILE
) -> bool:
    if headerfile_path is None:
        return False
    try:
        if headerfile_path.exists():
            with open(headerfile_path, "r") as handle:
                data = json.load(handle)
        else:
            data = {}
    except Exception:
        data = {}
    if data.get("Cookie") == cookie_value:
        return False
    data["Cookie"] = cookie_value
    with open(headerfile_path, "w") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
    return True
