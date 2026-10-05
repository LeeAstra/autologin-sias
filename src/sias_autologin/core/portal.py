"""Portable portal transport; no platform commands or credential storage."""
from dataclasses import dataclass
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

PORTAL_ORIGIN = "http://2.2.2.3"
PORTAL_PAGE = (
    PORTAL_ORIGIN
    + "/ac_portal/20210120210326/pc.html"
    + "?template=20210120210326&tabs=pwd&vlanid=0&_ID_=0"
    + "&switch_url=&url=http://2.2.2.3/homepage/index.html"
    + "&controller_type="
)
LOGIN_URL = PORTAL_ORIGIN + "/ac_portal/login.php"
CHECK_JUMP_URL = PORTAL_ORIGIN + "/httpscert/handler_checkjump"
INFO_URL = PORTAL_ORIGIN + "/homepage/info.php"
TIMEOUT_SECONDS = 12


@dataclass(frozen=True)
class PortalSettings:
    origin: str = PORTAL_ORIGIN
    page: str = PORTAL_PAGE
    login_url: str = LOGIN_URL
    jump_url: str = CHECK_JUMP_URL
    info_url: str = INFO_URL
    timeout: float = TIMEOUT_SECONDS

def build_portal_opener():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def request(opener, url: str, *, data: dict[str, str] | None = None,
            settings: PortalSettings | None = None) -> tuple[int, bytes]:
    settings = settings or PortalSettings()
    encoded = None if data is None else urlencode(data).encode("utf-8")
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoLogin-SIAS/1.0",
    }
    if data is not None:
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": settings.origin,
                "Referer": settings.page,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
    req = Request(url, data=encoded, headers=headers, method="POST" if encoded else "GET")
    with opener.open(req, timeout=settings.timeout) as response:
        return response.status, response.read()


class PortalClient:
    """Own transport settings; callers may subclass for recording or tests."""
    def __init__(self, settings: PortalSettings | None = None):
        self.settings = settings or PortalSettings()

    def build_opener(self):
        return build_portal_opener()

    def request(self, opener, url, *, data=None):
        return request(opener, url, data=data, settings=self.settings)

    def query_state(self):
        from .state import query_authentication_state
        return query_authentication_state(self)
