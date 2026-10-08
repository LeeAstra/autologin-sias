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

账号密码应来自调用者的本地安全配置。默认已认证时跳过登录；安装及独立向导验证保存的凭据使用 `validate_credentials=True`，这条配置适配路径不读取环境变量覆盖；普通运行仍保持原覆盖优先级。返回码沿用现有程序：0 成功，2 缺少凭据，4 HTTP 状态异常，5 拒绝，6 HTTP 异常，7 网络异常，8 无法确认，9 未预期错误。认证状态表示门户会话，不等同于互联网可访问。通用循环通过回调判断平台允许运行，不直接调用Windows API；维护模式说明见 [rc.4指南](releases/v1.3.0-rc.4.md)。

源码命令入口为 `python -m sias_autologin`（需 `PYTHONPATH=src`）；原 `src/auto_login_headless.py`、`src/install_autologin.py`、`src/credentials.py`、`src/app_version.py` 和 `scripts/` 下原脚本路径继续兼容。后台 EXE 名称、配置搜索顺序和日志位置保持兼容。选择新维护模式会显式更新任务触发器、参数和执行时限。新平台只需实现自己的调度和网络适配，复用 core；当前不提供 Linux/macOS 安装器。

Windows 构建使用 `scripts/build/Build-Installer.ps1`，任务脚本在 `scripts/windows/Install-AutoLoginTask.ps1`。实验源码复用核心与 Windows 适配，但不进入正式安装包。为保持连续实验版本一致，本次不重建已使用的监测 EXE。

验证包括 Linux 核心与旧接口回归，以及 Windows 单元测试、模拟门户、任务 XML 预览、安装包载荷和真实 EXE 的本机模拟回归。它们不替代真实校园网、UAC 和任务触发验收。

维护调用采用 `require_auth_required=True`：最新状态未知返回8等待，已认证跳过，需认证才提交。`before_auth` 回调在门户页面和凭据 POST 前检查平台许可；`on_submit` 只记录真实提交时刻。默认单次策略保持未知时尝试，安装验证保持强制提交。核心不引入 Windows 或时区调度依赖。

`runtime.monitor.LoginResult` 分别传递退出码、是否提交和是否确认；每轮结构化日志用 UUID 关联，时间保留时区。Windows 的 Read-MaintenanceEvidence.ps1 仅解析匹配任务开始时间和模式的完整当前轮次，缺失边界或异常结束返回无法确认。重复调用有独立编号，不能沿用其他轮次成功。

安装器的 InstallationLock 在旧状态读取前取得全局锁；同线程嵌套安装复用所有权，跨线程或跨进程竞争拒绝。只读版本及载荷检查无需锁。

Windows Wi-Fi 使用 `platforms/windows/network.py` 中的 WLAN API。函数每次重新打开会话、枚举接口并查询当前连接；所有 API 内存与句柄在 finally 中释放。固定32位枚举/DWORD和16位 WCHAR保证 ABI 一致。System32 限定 DLL 搜索；缓存仅包含函数绑定，不包含连接状态。断开为 wrong_network，服务、权限、查询错误或连接过渡为 network_unverified；任一网卡明确连接 UESTC 可提供目标网络证据。

维护循环的login回调必须返回LoginResult，真实提交记录决定冷却；未知跳过不消耗重试预算。整数返回值只保留在认证核心和单次CLI，由Windows适配包装；维护层不再猜测整数结果是否提交。文字响应成功使用完整格式白名单，结构化结果仍优先。

安装器按职责拆成三个模块：`installer.py` 负责交互向导和兼容入口，`deployment.py` 负责文件部署、备份、回滚和有限迁移清理，`tasks.py` 负责计划任务发现、完整 XML 快照和恢复。全局安装锁仍在读取旧状态前取得，部署入口也保留锁，嵌套调用复用所有权。任务命令集中生成；语法测试只解析、不执行，真实临时任务回归另外验证恢复行为。原安装入口和公开兼容函数保留，无新增运行依赖。

旧任务预检复用 Install-AutoLoginTask.ps1 的 ExportOnly 路径，先于停止任务和文件变更。迁移未取得新运行证据时保留旧文件；不把启动命令退出码当作维护成功。
