from pathlib import Path

from fuo_ytmusic import consts


def test_const_types():
    assert isinstance(consts.HEADER_FILE, Path)
    assert isinstance(consts.REQUIRED_COOKIE_FIELDS, list)
    assert all(isinstance(f, str) for f in consts.REQUIRED_COOKIE_FIELDS)
