import json

from fuo_ytmusic.headerfile import (
    PROFILE_GAIA_KEY,
    read_headerfile,
    update_profile_gaia_id,
    write_ytdlp_cookiefile,
    YtdlpCookiefileManager,
)


def test_update_profile_gaia_id_does_not_touch_cookiefile(tmp_path):
    headerfile = tmp_path / "ytmusic_header.json"
    headerfile.write_text(
        json.dumps({"Cookie": "SID=abc; HSID=def"}, ensure_ascii=True),
        encoding="utf-8",
    )
    write_ytdlp_cookiefile("SID=abc; HSID=def", headerfile)
    cookiefile = YtdlpCookiefileManager(headerfile).cookiefile_path
    assert cookiefile is not None
    before = cookiefile.read_text(encoding="utf-8")

    changed = update_profile_gaia_id("gaia-123", headerfile)

    assert changed is True
    headers = read_headerfile(headerfile)
    assert headers[PROFILE_GAIA_KEY] == "gaia-123"
    assert cookiefile.exists()
    assert cookiefile.read_text(encoding="utf-8") == before


def test_cookiefile_manager_write_and_delete(tmp_path):
    headerfile = tmp_path / "ytmusic_header.json"
    headerfile.write_text("{}", encoding="utf-8")
    manager = YtdlpCookiefileManager(headerfile)

    cookiefile = manager.write("SID=abc; HSID=def")
    assert cookiefile is not None
    assert cookiefile.exists()
    content = cookiefile.read_text(encoding="utf-8")
    assert ".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tabc" in content
    assert ".music.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tabc" in content
    assert ".google.com\tTRUE\t/\tTRUE\t0\tHSID\tdef" in content

    removed = manager.write("")
    assert removed is None
    assert not cookiefile.exists()


def test_cookiefile_manager_requires_existing_headerfile(tmp_path):
    headerfile = tmp_path / "ytmusic_header.json"
    manager = YtdlpCookiefileManager(headerfile)

    assert manager.cookiefile_path is None
    assert manager.write("SID=abc") is None
