"""SIAS campus network background login.

This version does not open a browser or use desktop automation, so it can run
while Windows is locked. Credentials are loaded from a .env file beside the
executable (or beside this source file when run as Python).
"""

from __future__ import annotations

import json
import argparse
import getpass
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import socket
import sys
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from app_version import VERSION
from credentials import load_env_file, write_env_file


APP_NAME = "AutoLogin_SIAS_Headless"
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
TIMEOUT_SECONDS = 12


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = application_dir()
LOG_PATH = BASE_DIR / "auto_login_headless.log"


def find_env_path() -> Path:
    """Prefer a private .env beside the EXE, with local-project fallbacks."""
    candidates = [BASE_DIR / ".env"]
    if BASE_DIR.parent != BASE_DIR:
        candidates.append(BASE_DIR.parent / ".env")
    candidates.append(Path.cwd() / ".env")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


ENV_PATH = find_env_path()


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=512 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
    except OSError:
        fallback_dir = Path(os.environ.get("TEMP", "."))
        fallback = fallback_dir / f"auto_login_headless_{os.getpid()}.log"
        try:
            handler = RotatingFileHandler(
                fallback,
                maxBytes=512 * 1024,
                backupCount=2,
                encoding="utf-8",
            )
        except OSError:
            # Last resort: keep console logging available; scheduled mode still works.
            handler = logging.NullHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if sys.stdout is not None:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)
    return logger


LOGGER = logging.getLogger(APP_NAME)
LOGGER.addHandler(logging.NullHandler())


def setup_env() -> int:
    """Interactive first-run configuration; never used by scheduled mode."""
    target = BASE_DIR / ".env"
    print(f"{APP_NAME} {VERSION} 配置向导")
    print(f"配置文件：{target}")
    if target.exists():
        answer = input("配置文件已存在，是否覆盖？[y/N]: ").strip().lower()
        if answer not in {"y", "yes", "是"}:
            print("已取消，不会修改现有配置。")
            return 0

    username = input("校园网账号：").strip()
    password = getpass.getpass("校园网密码（输入时不会显示）：")
    if not username or not password:
        print("账号和密码都不能为空。")
        return 2

    try:
        write_env_file(target, username, password)
    except OSError as exc:
        print(f"无法写入配置文件：{exc}")
        return 3

    global ENV_PATH
    ENV_PATH = target
    print("配置已保存，正在测试后台登录……")
    result = run_login()
    if result == 0:
        print("配置测试成功。之后可将无窗口 EXE 加入定时任务。")
    else:
        print(f"配置已保存，但登录测试失败（退出码 {result}）。请查看日志：{LOG_PATH}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIAS campus network background login")
    parser.add_argument("--setup", action="store_true", help="运行首次配置向导")
    parser.add_argument("--check", action="store_true", help="读取现有配置并测试登录")
    parser.add_argument("--version", action="store_true", help="显示版本")
    return parser.parse_args()


def rc4_hex(plain_text: str, key_text: str) -> str:
    """Match the portal's do_encrypt_rc4() JavaScript implementation."""
    key_text = str(key_text)
    if not key_text:
        raise ValueError("RC4 key is empty")

    key = [ord(key_text[i % len(key_text)]) for i in range(256)]
    sbox = list(range(256))

    j = 0
    for i in range(256):
        j = (j + sbox[i] + key[i]) % 256
        sbox[i], sbox[j] = sbox[j], sbox[i]

    a = 0
    b = 0
    output: list[str] = []
    for character in plain_text:
        a = (a + 1) % 256
        b = (b + sbox[a]) % 256
        sbox[a], sbox[b] = sbox[b], sbox[a]
        c = (sbox[a] + sbox[b]) % 256
        output.append(f"{ord(character) ^ sbox[c]:02x}")
    return "".join(output)


def build_portal_opener():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def request(opener, url: str, *, data: dict[str, str] | None = None) -> tuple[int, bytes]:
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
                "Origin": PORTAL_ORIGIN,
                "Referer": PORTAL_PAGE,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
    req = Request(url, data=encoded, headers=headers, method="POST" if encoded else "GET")
    with opener.open(req, timeout=TIMEOUT_SECONDS) as response:
        return response.status, response.read()


def response_indicates_success(body: bytes) -> tuple[bool | None, str]:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None, "empty response"

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        lowered = text.lower()
        if any(word in lowered for word in ("error", "fail", "invalid", "wrong", "密码错误")):
            return False, "failure marker in response"
        if any(word in lowered for word in ("success", "login ok", "登录成功")):
            return True, "success marker in response"
        return None, f"unrecognized response ({len(body)} bytes)"

    if isinstance(payload, dict):
        success = payload.get("success")
        if isinstance(success, bool):
            return success, "JSON success field"
        if success in (1, "1", "true", "True"):
            return True, "JSON success field"
        if success in (0, "0", "false", "False"):
            return False, "JSON success field"

        for key in ("result", "status", "code"):
            value = payload.get(key)
            if isinstance(value, bool):
                return value, f"JSON {key} field"
            normalized = str(value).lower()
            if normalized in ("success", "ok", "1", "200", "0"):
                return True, f"JSON {key} field"
            if normalized in ("fail", "failed", "error", "-1"):
                return False, f"JSON {key} field"

        message = str(payload.get("msg") or payload.get("message") or "")
        lowered = message.lower()
        if any(word in lowered for word in ("成功", "success", "already", "在线")):
            return True, "JSON message"
        if any(word in lowered for word in ("失败", "错误", "error", "fail", "密码")):
            return False, "JSON message"

    return None, "unrecognized JSON response"


def run_login() -> int:
    config = load_env_file(ENV_PATH)
    username = os.getenv("WLAN_USER") or config.get("WLAN_USER", "")
    password = os.getenv("WLAN_PWD") or config.get("WLAN_PWD", "")

    if not username or not password:
        LOGGER.error("Missing WLAN_USER or WLAN_PWD in %s", ENV_PATH)
        return 2

    auth_tag = str(int(time.time() * 1000))
    encrypted_password = rc4_hex(password, auth_tag)
    opener = build_portal_opener()

    try:
        portal_status, _ = request(opener, PORTAL_PAGE)
        LOGGER.info("Portal page status: %s", portal_status)

        login_status, login_body = request(
            opener,
            LOGIN_URL,
            data={
                "opr": "pwdLogin",
                "userName": username,
                "pwd": encrypted_password,
                "auth_tag": auth_tag,
                "rememberPwd": "0",
            },
        )
        success, reason = response_indicates_success(login_body)
        LOGGER.info(
            "Login response: status=%s bytes=%s result=%s (%s)",
            login_status,
            len(login_body),
            success,
            reason,
        )

        jump_status, jump_body = request(
            opener,
            CHECK_JUMP_URL,
            data={"vlanid": "0"},
        )
        LOGGER.info("Jump check: status=%s bytes=%s", jump_status, len(jump_body))

        if login_status != 200 or jump_status != 200:
            LOGGER.error("Portal returned an unexpected HTTP status")
            return 4
        if success is False:
            LOGGER.error("Portal explicitly rejected the login")
            return 5
        if success is None:
            LOGGER.error("Cannot confirm authentication from the portal response")
            return 8

        LOGGER.info("Background login request completed successfully")
        return 0
    except HTTPError as exc:
        LOGGER.error("HTTP error: %s %s", exc.code, exc.reason)
        return 6
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        LOGGER.error("Network error: %s", exc)
        return 7
    except Exception:
        LOGGER.exception("Unexpected error")
        return 9


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.version:
        print(f"{APP_NAME} {VERSION}")
        sys.exit(0)
    LOGGER = configure_logging()
    setup_executable = (
        getattr(sys, "frozen", False)
        and Path(sys.executable).stem.lower() == "autologin_sias_setup"
    )
    direct_setup = setup_executable and len(sys.argv) == 1
    if arguments.setup or direct_setup:
        setup_result = setup_env()
        if direct_setup:
            try:
                input("按回车键关闭窗口……")
            except EOFError:
                pass
        sys.exit(setup_result)
    # --check and the no-argument scheduled mode both execute one login check.
    sys.exit(run_login())
