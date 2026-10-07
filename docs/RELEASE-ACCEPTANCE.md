# v1.3.0 发布验收

状态：rc.6 候选，正式版尚未发布。测试不能证明绝对无缺陷；发布条件是自动化、打包、CI 与下面的真实使用流程均通过，无已知阻断问题。

## 自动化验收

运行 DEVELOPMENT 中的测试/构建命令，并运行 `python tests/check_task_recovery.py`。后者仅在 Windows 管理员环境创建唯一名称的临时任务验证恢复，结束后清理；不会修改 AutoLogin_SIAS。若输出 SKIP，此项仍待验证，不能记为通过。冻结安装器互斥使用 tests/check_installer_lock.py；证据混合/轮转使用 tests/Test-AcceptanceEvidence.ps1。

## 实机操作（按顺序）

先连接 UESTC，使用同一 Windows 账户允许 UAC。使用 rc.6 安装器，失败即停止后续测试并按模板报告，不要手动删除文件/任务。

1. A 原位升级：运行安装器，填当前安装目录，模式选 2，保留旧凭据，确认安装。应显示部署完成；等待60秒再采集状态，任务启用，参数为 `--maintain night`。白天正常退出，不要求立即登录。
2. B 迁移与持续模式：再次运行同一安装器，填一个新的绝对目录（普通、未启用 EFS 加密的本地目录），选 1 并保留凭据。应显示部署完成；等待60秒再采集状态，旧目录仅后台 EXE、任务脚本和独立 .env 被清理，其他文件保留，新目录存在三个文件。
3. C 断网重连：连接 UESTC 后等待 60 秒，观察任务运行；手动断开 Wi-Fi，等待 60 秒，确认任务退出；重新连接 UESTC，等待 60 秒，确认任务重新运行。不要关闭 WLAN 事件日志。
4. D 睡眠恢复：保持模式 1 和 UESTC，让电脑睡眠至少 1 分钟，恢复后等待 60 秒；确认任务恢复运行。若没有恢复，先运行状态采集再报告，不能用手动启动替代通过。
5. E 恢复夜间模式并实测：运行安装器，使用最终安装目录，选 2，确认任务参数 `--maintain night`。夜间保持电脑唤醒、连接 UESTC，覆盖 02:55～03:15；次日上午采集状态。应看到启动、认证状态、需要时登录后恢复、窗口结束退出，返回码 0 且无漏执行。没有观察到登出则填写未观察到，不能记为重新登录成功。

每一步结束后，以同一账户打开管理员 PowerShell，在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\Get-AcceptanceStatus.ps1
```

脚本只读，输出任务设置和匹配本次运行的带时间事件，不输出账号密码。schema 必须是 autologin-acceptance-v2；版本来自本轮日志，旧版无结构化证据时为 UNKNOWN_VERSION。evidence_status=unconfirmed 不能填 PASS。evidence 包含 run_id、started_at、ended_at、observed_logout、authentication_submitted、recovery_confirmed；没有认证提交不能填写重新登录成功。把每步的 JSON 保存供回复；步骤 C 要采集断开后、重连后各一次。运行中的 last_result 可能是 267009（0x41301），表示正在运行，不能据此判失败；结合 task_state 判断。

## 固定回复模板

复制后仅填写 PASS / FAIL / NOT_RUN，无法确认填 NOT_RUN。不要把预期结果当实测结果。

```text
验收版本：1.3.0-rc.6
A 原位升级：
B 迁移及旧文件清理：
C 断网退出及重连启动：
D 睡眠恢复：
E 夜间窗口运行：
E 是否观察到登出并重新登录：是 / 否 / 未观察到登出
当前最终模式：night / continuous
各步状态JSON：按 A、B、C断开、C重连、D、E 的顺序粘贴
异常发生步骤：无 / A / B / C / D / E
异常提示原文：无 / 原样粘贴（不含凭据）
```

如需删除旧安装目录额外文件、修改电源策略或使用全新账户测试，另行明确步骤；本轮不要求这些操作。完整 UAC 向导通过步骤 A/B 实测。未完成项目保持待验收，正式版不得标记为已验证。
