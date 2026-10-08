# 开发指南

面向修改源码或移植平台的开发者，基于已发布 v1.3.0。用户安装无需 Python；贡献和发布规则见[维护与发布](MAINTENANCE.md)。

## 结构和入口

| 位置 | 职责 |
|---|---|
| `src/sias_autologin/core/` | 门户传输、响应判断、状态查询及一次认证操作 |
| `src/sias_autologin/runtime/` | 平台无关维护循环、窗口、等待和提交冷却 |
| `src/sias_autologin/platforms/windows/` | WLAN API、维护入口、互斥、安装事务及任务管理 |
| `src/sias_autologin/cli.py`、`config.py` | 命令行、日志、配置读写与凭据选择 |
| `scripts/windows/`、`scripts/build/` | 任务 PowerShell 脚本及构建脚本 |
| `tools/experiments/` | 不随安装部署的监测、诊断和测量工具 |

`python -m sias_autologin` 是源码命令入口。`src/auto_login_headless.py` 和 `src/install_autologin.py` 是保留的兼容/打包入口；`src/credentials.py`、`src/app_version.py` 和顶层 `scripts/` 转发脚本同样保留兼容。唯一版本来源是 `src/sias_autologin/version.py`。[调用关系与关键策略](ARCHITECTURE.md)。

## 在源码中运行

以下在 **Windows PowerShell 的仓库根目录**执行，使用 Python 3.13（当前 CI 版本）。建立独立虚拟环境，只影响该仓库的 `.venv`：

```powershell
python -m venv .venv
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& $python -m sias_autologin --version
```

预期显示 `AutoLogin_SIAS_Headless 1.3.0`。运行代码只依赖标准库，打包工具另外安装。使用自己的 Python 路径时替换 `$python`，不要改系统环境变量。

下面是**可选真实认证操作**：连接 UESTC 后运行，会写 `src/.env` 并提交本次凭据验证；已有文件先询问是否覆盖，不创建计划任务：

```powershell
& $python -m sias_autologin --setup
```

需要测试一次登录可用 `--check`，它可能提交认证，**不是只读状态查询**。无参数同样执行一次检测/登录。维护入口 `--maintain night` 或 `--maintain continuous` 仅 Windows 可用；已有正式维护实例时不要并行测试。`--validate-credentials` 强制验证保存配置，即使在线也提交。发布的 Headless EXE 无控制台，普通用户交互配置使用完整安装器。

Linux/macOS 可复用 `core` 和 `runtime`，模块导入需将 `src` 加入 `PYTHONPATH`；本项目目前没有这些平台的维护安装器。不要把 Windows 维护命令当作跨平台支持。

## 测试

从仓库根目录执行源码和实验回归，使用合成夹具，不需要真实账号：

```powershell
& $python -m unittest discover -s tests -v
& $python -m unittest discover -s tools/experiments/login-diagnostics -v
& $python -m unittest discover -s tools/experiments/login-monitor -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-TaskPreview.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-AcceptanceEvidence.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-AcceptanceStatus.ps1
```

任务预览只生成临时 XML，不注册任务；证据和状态测试使用合成数据。依赖本地捕获资料的实验测试可能跳过，应保留跳过原因而非报告全部实机场景通过。

## Windows 构建与冻结验证

**构建会更新本地 `packaging/dist/`，不会更新已安装程序或上传 Release。** 使用干净提交，在上面的虚拟环境中执行：

```powershell
& $python -m pip install -r requirements-build.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Installer.ps1 -Python $python
& $python tests/check_task_commands.py
& $python tests/check_installer_lock.py
& $python tests/check_bundle.py
& $python tests/check_live_wlan.py
& $python tests/check_task_recovery.py
& $python tests/check_frozen_login.py
```

脚本按顺序构建后台和安装器，输出两个 EXE、`SHA256SUMS.txt`、`BUILD-INFO.json`。实际实现脚本在 `scripts/build/`；旧路径仅转发，不另维护一套逻辑。

冻结认证使用固定 loopback 模拟服务；测试专用构建的模拟 WLAN、配置输入及代理钩子不进入生产包。`check_live_wlan.py` 会查询真实 WLAN，未确认 UESTC 时有明确跳过；它不能替代实际任务账户验收。

**管理员权限测试会创建、运行及删除隔离临时任务和目录。** `check_task_recovery.py`、冻结安装矩阵不触碰正式 `AutoLogin_SIAS`；覆盖两种模式新装、原位、迁移、在线错误凭据后的恢复、不支持旧任务及其他路径同名进程保护。普通权限可能跳过任务测试；Windows CI 要求管理员矩阵实际通过。完整检查以[CI 工作流](../.github/workflows/windows.yml)为准。

## 扩展平台或协议

协议适配在 `core/portal.py`、`state.py` 和 `authentication.py`，先用合成响应及模拟服务验证。平台移植实现自己的网络许可、调度和单实例机制，并向 `runtime` 注入回调；不要在核心导入 Windows API。

新功能需分别说明协议、任务触发和电源条件的影响。自动化不能替代真实网络、UAC、连接事件和睡眠验收。[v1.3.0 验收](releases/v1.3.0-acceptance.md)记录实际覆盖和限制，[历史开发记录](history/DEVELOPMENT-THROUGH-2026-10-07.md)保留候选演进。
