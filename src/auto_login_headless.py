"""Compatibility entry point; portable business code lives in sias_autologin.core."""
import logging
import os
import sys
import time
from sias_autologin import cli
from sias_autologin.version import VERSION
from sias_autologin.config import load_env_file, write_env_file
from sias_autologin.core import portal, state, service
from sias_autologin.core.authentication import rc4_hex, response_indicates_success
from sias_autologin.core.portal import (
    PORTAL_ORIGIN, PORTAL_PAGE, LOGIN_URL, CHECK_JUMP_URL, INFO_URL,
    TIMEOUT_SECONDS, PortalSettings, PortalClient, build_portal_opener,
)

APP_NAME = "AutoLogin_SIAS_Headless"
application_dir = cli.application_dir
BASE_DIR = application_dir()
LOG_PATH = BASE_DIR / "auto_login_headless.log"

def find_env_path():
    return cli.find_env_path(BASE_DIR)

ENV_PATH = find_env_path()
LOGGER = logging.getLogger(APP_NAME)
LOGGER.addHandler(logging.NullHandler())

def configure_logging():
    return cli.configure_logging(LOG_PATH, APP_NAME)

def setup_env():
    return cli.setup_env(sys.modules[__name__])

parse_args = cli.parse_args

def settings():
    return PortalSettings(PORTAL_ORIGIN, PORTAL_PAGE, LOGIN_URL, CHECK_JUMP_URL,
                          INFO_URL, TIMEOUT_SECONDS)

def request(opener, url, *, data=None):
    return portal.request(opener, url, data=data, settings=settings())

def authentication_state(status, body):
    return state.authentication_state(status, body, portal_origin=PORTAL_ORIGIN)

class _CompatibilityClient(PortalClient):
    def build_opener(self):
        return build_portal_opener()

    def request(self, opener, url, *, data=None):
        return request(opener, url, data=data)

    def query_state(self):
        return query_authentication_state()

def query_authentication_state():
    return state.query_authentication_state(_CompatibilityClient(settings()))

def run_login(*, validate_credentials=False):
    started = time.monotonic()
    try:
        config = load_env_file(ENV_PATH)
        username = os.getenv("WLAN_USER") or config.get("WLAN_USER", "")
        password = os.getenv("WLAN_PWD") or config.get("WLAN_PWD", "")
    except Exception as exc:
        LOGGER.error("Unexpected error: %s", type(exc).__name__)
        LOGGER.info(
            "Authentication summary: prior_state=not_checked action=none "
            "login_response_result=None post_state=not_checked confirmed=False "
            "exit_code=9 duration=%.3fs", time.monotonic() - started,
        )
        return 9
    return service.ensure_authenticated(username, password, client=_CompatibilityClient(settings()),
                                        logger=LOGGER, validate_credentials=validate_credentials)

if __name__ == "__main__":
    sys.exit(cli.main(sys.modules[__name__]))
