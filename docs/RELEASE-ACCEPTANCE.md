# v1.3.0 发布验收

状态：rc.7 候选，正式版尚未发布。测试不能证明绝对无缺陷；发布条件是自动化、打包、CI 与下面的真实使用流程均通过，无已知阻断问题。

## 自动化验收

先运行 `python tests/check_task_commands.py`（只解析安装器生成的命令，不修改任务）。运行 DEVELOPMENT 中的测试/构建命令，并运行 `python tests/check_task_recovery.py`。后者仅在 Windows 管理员环境创建唯一名称的临时任务验证恢复，结束后清理；不会修改 AutoLogin_SIAS。若输出 SKIP，此项仍待验证，不能记为通过。冻结安装器互斥使用 tests/check_installer_lock.py；证据混合/轮转使用 tests/Test-AcceptanceEvidence.ps1。

## 实机操作（按顺序）

先保存旧状态 JSON；关闭独立实验监测，避免同时认证。先连接 UESTC，使用同一 Windows 账户允许 UAC。使用 rc.7 安装器，失败即停止后续测试并按模板报告，不要手动删除文件/任务。

1. A 原位升级：运行安装器，填当前安装目录 `D:\Apps\AutoLogin_SIAS`（如实际目录不同，以现有任务路径为准），模式选 2，保留旧凭据，确认安装。应显示部署完成；等待60秒再采集状态，任务启用，参数为 `--maintain night`。白天正常退出，不要求立即登录。
2. B 迁移与持续模式：再次运行同一安装器，填 `D:\Apps\AutoLogin_SIAS-Acceptance` 等新的绝对目录（普通、未启用 EFS 加密的本地目录），选 1 并保留凭据。应显示部署完成；等待60秒再采集状态，旧目录仅后台 EXE、任务脚本和独立 .env 被清理，其他文件保留，新目录存在三个文件。
3. C 断网重连：连接 UESTC 后等待 60 秒，观察任务运行；手动断开 Wi-Fi，等待 60 秒，确认任务退出；重新连接 UESTC，等待 60 秒，确认任务重新运行。如可用，再连接其他 Wi-Fi 等待 60 秒，确认维护程序退出且没有认证提交，再重连 UESTC。不要关闭 WLAN 事件日志。
4. D 睡眠恢复：保持模式 1 和 UESTC，让电脑睡眠至少 1 分钟，恢复后等待 60 秒；确认任务恢复运行。若没有恢复，先运行状态采集再报告，不能用手动启动替代通过。
5. E 恢复夜间模式并实测：运行安装器，使用最终安装目录 `D:\Apps\AutoLogin_SIAS`，选 2，确认任务参数 `--maintain night`。夜间保持电脑唤醒、连接 UESTC，覆盖 2026-10-08（或实际测试日）02:55～03:15；次日上午在切换 Wi-Fi、重装或手动启动前采集状态，避免最新运行替代夜间证据。若已触发新运行，同时保留完整轮转日志供核对。应看到启动、认证状态、需要时登录后恢复、窗口结束退出，返回码 0 且无漏执行。没有观察到登出则填写未观察到，不能记为重新登录成功。

开始步骤 A 前，以同一账户打开管理员 PowerShell，在 `D:\OneDrive\Temp\Learning\autologin` 中运行。先建立保存函数并保存 before，再按上文完成各步，每步用不同标签保存 JSON：

```powershell
Set-Location 'D:\OneDrive\Temp\Learning\autologin'
$acceptanceFolder = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AutoLogin-rc7-验收'
New-Item -ItemType Directory -Path $acceptanceFolder -Force | Out-Null
function Save-AutoLoginAcceptance([string]$Label) {
    & .\scripts\windows\Get-AcceptanceStatus.ps1 |
        Set-Content -LiteralPath (Join-Path $acceptanceFolder ($Label + '.json')) -Encoding UTF8
}
Save-AutoLoginAcceptance 'before'
# 完成相应步骤后分别执行，不能一次运行下面所有命令：
# Save-AutoLoginAcceptance 'A'
# Save-AutoLoginAcceptance 'B'
# Save-AutoLoginAcceptance 'C-disconnected'
# Save-AutoLoginAcceptance 'C-other-wifi'
# Save-AutoLoginAcceptance 'C-reconnected'
# Save-AutoLoginAcceptance 'D'
# Save-AutoLoginAcceptance 'E'
```


脚本只读，输出任务设置和匹配本次运行的带时间事件，不输出账号密码。schema 必须是 autologin-acceptance-v2；版本来自本轮日志，旧版无结构化证据时为 UNKNOWN_VERSION。evidence_status=unconfirmed 不能填 PASS。evidence 包含 run_id、started_at、ended_at、observed_logout、authentication_submitted、recovery_confirmed；没有认证提交不能填写重新登录成功。把每步的 JSON 保存供回复；步骤 C 要采集断开后、重连后各一次。运行中的 last_result 可能是 267009（0x41301），表示正在运行，不能据此判失败；结合 task_state 判断。

## 固定回复模板

复制后仅填写 PASS / FAIL / NOT_RUN，无法确认填 NOT_RUN。不要把预期结果当实测结果。

```text
验收版本：1.3.0-rc.7
A 原位升级：
B 迁移及旧文件清理：
C 断网退出：
C 其他 Wi-Fi 退出（没有可用网络填 NOT_RUN）：
C 重连自动启动：
D 睡眠恢复：
E 夜间窗口运行：
E 是否观察到登出并重新登录：是 / 否 / 未观察到登出
多无线网卡实测：PASS / FAIL / NOT_RUN（只有具备此硬件时测试）
当前最终目录：
当前最终模式：night / continuous
各步状态JSON：按 A、B、C断开、C其他网络（如有）、C重连、D、E 的顺序粘贴
异常发生步骤：无 / A / B / C / D / E
异常提示原文：无 / 原样粘贴（不含凭据）
```

如需删除旧安装目录额外文件、修改电源策略或使用全新账户测试，另行明确步骤；本轮不要求这些操作。完整 UAC 向导通过步骤 A/B 实测。未完成项目保持待验收，正式版不得标记为已验证。

## 不能由自动化替代的测试

A/B 的真实 UAC 向导、凭据验证和目录迁移，C 的网络事件触发，D 的睡眠恢复，E 的自然登出恢复需要本机操作。自动化已覆盖 WLAN 服务不可用、未知状态、多网卡与 API 资源释放路径；不要求为测试关闭本机 WLAN 服务。具备多无线网卡时可补测一个接口连接 UESTC、另一个接口连接其他网络，并记录接口组合。未具备的硬件测试如实记 NOT_RUN。

白天夜间模式退出属于预期；没有登出证据仍需继续夜间观测。认证失败若有实际提交，重试间隔至少15秒；未提交的未知状态按正常5秒检测。最终发布必须核对当前提交的 CI、候选包哈希及 A～E 证据，不能用历史运行的成功代替本轮验收。
