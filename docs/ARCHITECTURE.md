# 代码结构与跨平台开发

```text
src/sias_autologin/
  core/portal.py          HTTP、Cookie 和门户地址
  core/authentication.py RC4 和登录响应解析
  core/state.py          门户认证状态查询与判定
  core/service.py        先检测、必要时登录、再次确认
  runtime/monitor.py     通用循环、时间窗口与重试策略
  config.py              兼容现有凭据文件格式
  cli.py                 参数、配置向导与日志
  version.py             唯一版本来源
  platforms/windows/     安装、Wi-Fi、维护入口与单实例
scripts/windows/         Windows 任务命令脚本
scripts/build/           EXE 构建命令脚本
tools/experiments/       独立夜间监测与诊断工具
```

核心只依赖 Python 标准库，不读取配置文件、不执行 Windows 命令。调用者提供凭据、日志和可选 PortalClient；网络请求保留原有系统代理行为。安装器、计划任务、Wi-Fi 检测和防休眠仍是 Windows 功能。

在仓库根目录将 `src` 加入 `PYTHONPATH` 后，可直接使用：

```python
from sias_autologin.core.portal import PortalClient
from sias_autologin.core.service import ensure_authenticated

client = PortalClient()
state, reason = client.query_state()  # 只查询，不登录
code = ensure_authenticated(username, password, client=client)
```

账号密码应来自调用者的本地安全配置。默认已认证时跳过登录；安装时验证新凭据使用 `validate_credentials=True`。返回码沿用现有程序：0 成功，2 缺少凭据，4 HTTP 状态异常，5 拒绝，6 HTTP 异常，7 网络异常，8 无法确认，9 未预期错误。认证状态表示门户会话，不等同于互联网可访问。通用循环通过回调判断平台允许运行，不直接调用Windows API；维护模式说明见 [rc.2指南](releases/v1.3.0-rc.2.md)。

源码命令入口为 `python -m sias_autologin`（需 `PYTHONPATH=src`）；原 `src/auto_login_headless.py`、`src/install_autologin.py`、`src/credentials.py`、`src/app_version.py` 和 `scripts/` 下原脚本路径继续兼容。后台 EXE 名称、配置搜索顺序和日志位置保持兼容。选择新维护模式会显式更新任务触发器、参数和执行时限。新平台只需实现自己的调度和网络适配，复用 core；当前不提供 Linux/macOS 安装器。

Windows 构建使用 `scripts/build/Build-Installer.ps1`，任务脚本在 `scripts/windows/Install-AutoLoginTask.ps1`。实验源码复用核心与 Windows 适配，但不进入正式安装包。为保持连续实验版本一致，本次不重建已使用的监测 EXE。

验证包括 Linux 核心与旧接口回归，以及 Windows 单元测试、模拟门户、任务 XML 预览、安装包载荷和真实 EXE 的本机模拟回归。它们不替代真实校园网、UAC 和任务触发验收。
