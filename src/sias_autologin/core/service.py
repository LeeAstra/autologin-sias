"""One portable authentication operation; no CLI, files or Windows imports."""
import logging
import socket
import time
from urllib.error import HTTPError, URLError
from .portal import PortalClient
from .authentication import rc4_hex, response_indicates_success

def ensure_authenticated(username: str, password: str, *, client: PortalClient | None = None,
                         logger: logging.Logger | None = None, validate_credentials: bool = False,
                         require_auth_required: bool = False, before_auth=None, on_submit=None) -> int:
    client = client or PortalClient()
    logger = logger or logging.getLogger("AutoLogin_SIAS_Headless")
    started = time.monotonic()
    outcome = {"prior_state": "not_checked", "action": "none",
               "login_response_result": None, "post_state": "not_checked",
               "confirmed": False}
    code = 9
    try:
        code = _run_login_once(username, password, client, logger, outcome, validate_credentials=validate_credentials,
                               require_auth_required=require_auth_required, before_auth=before_auth, on_submit=on_submit)
        return code
    except Exception as exc:
        logger.error("Unexpected error: %s", type(exc).__name__)
        return code
    finally:
        logger.info(
            "Authentication summary: prior_state=%s action=%s "
            "login_response_result=%s post_state=%s confirmed=%s exit_code=%s duration=%.3fs",
            outcome["prior_state"], outcome["action"], outcome["login_response_result"],
            outcome["post_state"], outcome["confirmed"], code, time.monotonic() - started,
        )


def _run_login_once(username, password, client, logger, outcome: dict, *, validate_credentials=False,
                    require_auth_required=False, before_auth=None, on_submit=None) -> int:
    if not username or not password:
        logger.error("Missing WLAN_USER or WLAN_PWD")
        return 2

    prior_state, prior_reason = client.query_state()
    outcome["prior_state"] = prior_state
    logger.info("Authentication before login: prior_state=%s reason=%s", prior_state, prior_reason)
    if prior_state == "authenticated" and not validate_credentials:
        outcome.update(action="skip", confirmed=True)
        logger.info("already_authenticated: skipping login; portal authentication confirmed")
        return 0
    if require_auth_required and not validate_credentials and prior_state != "auth_required":
        outcome["action"] = "wait"
        logger.info("Maintenance policy: latest state is not auth_required; waiting")
        return 8
    outcome["action"] = "login"
    logger.info("Credential validation requested: %s", validate_credentials)

    auth_tag = str(int(time.time() * 1000))
    encrypted_password = rc4_hex(password, auth_tag)
    opener = client.build_opener()

    try:
        if before_auth is not None and not before_auth():
            outcome["action"] = "wait"
            return 8
        portal_status, _ = client.request(opener, client.settings.page)
        logger.info("Portal page status: %s", portal_status)

        # The page fetch may cross the boundary; gate the credential POST too.
        if before_auth is not None and not before_auth():
            outcome["action"] = "wait"
            return 8
        if on_submit is not None:
            on_submit()
        login_status, login_body = client.request(
            opener,
            client.settings.login_url,
            data={
                "opr": "pwdLogin",
                "userName": username,
                "pwd": encrypted_password,
                "auth_tag": auth_tag,
                "rememberPwd": "0",
            },
        )
        success, reason = response_indicates_success(login_body)
        outcome["login_response_result"] = success
        logger.info(
            "Login response: status=%s bytes=%s result=%s (%s)",
            login_status,
            len(login_body),
            success,
            reason,
        )

        jump_status, jump_body = client.request(
            opener,
            client.settings.jump_url,
            data={"vlanid": "0"},
        )
        logger.info("Jump check: status=%s bytes=%s", jump_status, len(jump_body))

        if login_status != 200 or jump_status != 200:
            logger.error("Portal returned an unexpected HTTP status")
            return 4
        if success is False:
            logger.error("Portal explicitly rejected the login")
            return 5
        if success is None:
            logger.error("Cannot confirm authentication from the portal response")
            return 8

        post_state, post_reason = client.query_state()
        outcome["post_state"] = post_state
        outcome["confirmed"] = post_state == "authenticated"
        logger.info("Authentication after login: post_state=%s reason=%s", post_state, post_reason)
        if post_state != "authenticated":
            logger.error("Login response succeeded but portal authentication is not confirmed")
            return 8

        logger.info("Background login request completed successfully")
        return 0
    except HTTPError as exc:
        logger.error("HTTP error: %s", exc.code)
        return 6
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        logger.error("Network error: %s", type(exc).__name__)
        return 7
    except Exception as exc:
        logger.error("Unexpected error: %s", type(exc).__name__)
        return 9
