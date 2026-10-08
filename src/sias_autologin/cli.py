"""Command-line configuration and logging, separate from authentication."""
import argparse
import getpass
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

def application_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

from .config import find_env_path

def configure_logging(log_path, app_name="AutoLogin_SIAS_Headless") -> logging.Logger:
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        handler = RotatingFileHandler(
            log_path,
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


def setup_env(app) -> int:
    """Interactive first-run configuration; never used by scheduled mode."""
    target = app.BASE_DIR / ".env"
    print(f"{app.APP_NAME} {app.VERSION} 配置向导")
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
        app.write_env_file(target, username, password)
    except ValueError as exc:
        print(f"配置无效：{exc}")
        return 2
    except OSError as exc:
        print(f"无法写入配置文件：{exc}")
        return 3

    app.ENV_PATH = target
    print("配置已保存，正在验证本次保存的账号密码……")
    result = app.run_login(validate_credentials=True)
    if result == 0:
        print("配置测试成功。之后可将无窗口 EXE 加入定时任务。")
    else:
        print(f"配置已保存，但登录测试失败（退出码 {result}）。请查看日志：{app.LOG_PATH}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIAS campus network background login")
    parser.add_argument("--setup", action="store_true", help="运行首次配置向导")
    parser.add_argument("--check", action="store_true", help="读取现有配置并测试登录")
    parser.add_argument("--validate-credentials", action="store_true", help="提交并验证配置凭据，即使当前已认证")
    parser.add_argument("--version", action="store_true", help="显示版本")
    parser.add_argument('--maintain', choices=('continuous', 'night'), help='Windows maintenance mode')
    parser.add_argument('--window-start', default='02:55')
    parser.add_argument('--window-end', default='03:15')
    args = parser.parse_args()
    from datetime import time
    try:
        start, end = time.fromisoformat(args.window_start), time.fromisoformat(args.window_end)
        if start == end or start.tzinfo or end.tzinfo:
            raise ValueError()
    except ValueError:
        parser.error('Window times must be distinct local HH:MM values')
    if args.maintain and (args.setup or args.check or args.validate_credentials):
        parser.error('Maintenance cannot be combined with setup or credential checks')
    return args


def main(app=None):
    if app is None:
        import auto_login_headless as app
    arguments = parse_args()
    if arguments.version:
        print(f"{app.APP_NAME} {app.VERSION}")
        return 0
    app.LOGGER = app.configure_logging()
    setup_executable = (
        getattr(sys, "frozen", False)
        and Path(sys.executable).stem.lower() == "autologin_sias_setup"
    )
    direct_setup = setup_executable and len(sys.argv) == 1
    if arguments.setup or direct_setup:
        setup_result = app.setup_env()
        if direct_setup:
            try:
                input("按回车键关闭窗口……")
            except EOFError:
                pass
        return setup_result
    if arguments.maintain:
        from .platforms.windows.runner import run
        return run(app, arguments)
    # --check and the no-argument scheduled mode both execute one login check.
    return app.run_login(validate_credentials=arguments.validate_credentials)
