from pathlib import Path
from feeluown.consts import DATA_DIR
HEADER_FILE = Path(DATA_DIR) / "ytmusic_header.json"
REQUIRED_COOKIE_FIELDS = [
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-3PAPISID",
    "LOGIN_INFO",
    "__Secure-1PAPISID",
    "SID",
    "__Secure-1PSID",
    "__Secure-3PSID",
    "__Secure-3PSIDCC",
]
