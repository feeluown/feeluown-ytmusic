from pathlib import Path

HEADER_FILE = Path.home() / '.FeelUOwn' / 'data' / 'ytmusic_header.json'
COOKIE_FILE = Path.home() / '.FeelUOwn' / 'data' / 'ytmusic_cookie.json'
REQUIRED_COOKIE_FIELDS = ['HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-3PAPISID', 'LOGIN_INFO', '__Secure-1PAPISID',
                          'SID', '__Secure-1PSID', '__Secure-3PSID', '__Secure-3PSIDCC']
