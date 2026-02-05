import json

from fuo_ytmusic.consts import HEADER_FILE


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
