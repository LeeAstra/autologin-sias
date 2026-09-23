# Windows 自动任务：指定 Wi-Fi + 每天重新认证

这两个用途可以同时存在：连接 `UESTC` 后运行一次；每天 **04:10** 再运行一次，处理校园网凌晨认证失效。使用 `AutoLogin_SIAS_Headless.exe`，不要使用旧版浏览器自动化程序。

## 一条命令安装或更新

单文件安装包 `AutoLogin_SIAS_Installer.exe` 已整合下述脚本，完成账号输入和登录验证后会自动调用，无需再手动执行命令。它将后台程序安装到 `%LOCALAPPDATA%\AutoLogin_SIAS`；新任务与已有任务的处理规则和下文一致。源码构建方法见 README，既有 Release 不会自动包含新安装包。

先运行配置向导，配置自己的 `.env`，并确认手动运行后台 EXE 能认证成功。把 EXE 和配置放在固定、已下载到本机的目录中。下载仓库中的 [Install-AutoLoginTask.ps1](../scripts/Install-AutoLoginTask.ps1)，或使用仓库内的副本。

使用**同一个 Windows 账户**以管理员身份打开 PowerShell，在仓库根目录执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-AutoLoginTask.ps1 -ExePath "C:\AutoLogin\AutoLogin_SIAS_Headless.exe"
```

如果单独下载脚本，请把 `-File` 改为脚本实际路径。`ExecutionPolicy Bypass` 仅用于该次 PowerShell 进程，不修改系统执行策略。脚本不会立即启动登录程序，也不会读取、输出或更改校园网密码。

默认任务名 `AutoLogin_SIAS`，SSID 为 `UESTC`。新建任务时可以使用 `-SSID "你的校园网名称" -DailyAt "04:10" -TaskName "AutoLogin_SIAS"` 自定义。SSID 区分大小写；同时包含单引号和双引号的名称不受此脚本支持。

| 项目 | 新建任务默认设置 |
|---|---|
| Wi-Fi 触发 | WLAN 事件 `8001` 或 `11005`，且 `SSID = UESTC` |
| 网络准备时间 | 事件后延迟 30 秒 |
| 定时触发 | 每天 04:10 |
| 运行账户 | 执行安装命令的账户，S4U，不保存 Windows 密码，最低权限 |
| 重复触发 | 忽略新实例，让当前认证完成 |
| 超时与重试 | 最长运行 3 分钟；失败后每隔 5 分钟重试，最多 3 次 |
| 电源 | 电池上可运行，不主动唤醒电脑 |
| 错过定时 | 恢复可运行状态后补跑，可能延迟 |
| 开机、用户登录触发 | 不新增 |

S4U 适用于本机可读文件和本程序现有 HTTP 门户认证方式，不提供 Windows 集成网络身份验证能力，不能依赖它访问需 Windows 凭据的共享盘或加密文件。若换一个管理员账户执行，新任务也会属于那个账户，请勿这样安装。

**更新已有任务时：**先导出 XML 备份到 `%LOCALAPPDATA%\AutoLogin_SIAS\TaskBackups`，再更新 WLAN 事件、30 秒延迟、重复实例策略及 EXE/工作目录。保留已有每天 04:10、旧的一次性时间触发、其他触发器、账户、重试及电源设置，不自动补建或改写已有时间计划。`-DailyAt` 仅用于新建任务。多个 WLAN 触发器、带参数的旧操作或需密码的运行账户会要求手动处理，避免静默覆盖特殊配置。

先预览，不写入任务：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-AutoLoginTask.ps1 -ExePath "C:\AutoLogin\AutoLogin_SIAS_Headless.exe" -ExportOnly ".\task-preview.xml"
```

也支持 `-WhatIf`。生成的 XML 包含本机账户标识和路径，不要提交到仓库。

## 手动配置

按 `Win + R`，输入 `taskschd.msc`，选择“创建任务”，或打开已有任务属性。

1. **常规**：名称 `AutoLogin_SIAS`。后台版可选择“不管用户是否登录都要运行”；不用管理员运行权限。若采用保存密码模式，输入的是 Windows 密码，不是校园网密码。仅在用户登录时运行也支持锁屏，但不覆盖登录前。
2. **操作**：程序填写 EXE 完整路径；参数留空；“起始于”填写 EXE 所在文件夹，例如 `C:\AutoLogin`。
3. **定时触发器**：每天 04:10，启用。已有一次性触发器可以保留；旧日期的一次性触发不会变成每天重复执行。
4. **Wi-Fi 触发器**：选择“发生事件时”→“自定义”→“新建事件筛选器”→“XML”→勾选“手动编辑查询”，粘贴下方查询；高级设置延迟 30 秒。
5. **条件**：取消“只有使用交流电源才启动”和“切换到电池时停止”；不要额外要求 Windows 判定特定网络可用。默认不勾选唤醒计算机。
6. **设置**：允许按需运行；启用错过计划后补跑；失败后每 5 分钟重试 3 次；超过 3 分钟停止；已运行时选择“不启动新实例”。

```xml
<QueryList>
  <Query Id="0" Path="Microsoft-Windows-WLAN-AutoConfig/Operational">
    <Select Path="Microsoft-Windows-WLAN-AutoConfig/Operational">
      *[System[(EventID=8001 or EventID=11005)]]
      and
      *[EventData[Data[@Name='SSID']='UESTC']]
    </Select>
  </Query>
</QueryList>
```

`8001` 表示无线连接成功；`11005` 表示无线安全验证成功。部分快速启动或低功耗恢复过程中，会出现 `11005` 而没有新的 `8001`，只监听后者就会漏掉。`11005` 也可能在重新验证时出现，并不代表已经取得 IP 或校园网认证成功，因此延迟运行并保留失败重试。两个事件可能接连到达，“不启动新实例”避免中断认证，但不会把忽略的触发排队补跑。

此筛选检查的是**事件中的 SSID**。延迟或重试期间切换网络，不会取消已安排的运行；程序目前没有执行前再次核对 SSID 的保证。每天的时间触发独立于 Wi-Fi 事件筛选。

## 睡眠、关机与快速启动

- 仅锁屏或关屏、系统仍在运行时，可以按时执行。
- 默认不唤醒：04:10 处于睡眠或休眠时不会为本任务主动醒来；恢复后允许补跑，但不保证立即执行。
- 若确实需要 04:10 唤醒，手动勾选“唤醒计算机运行此任务”，并核对系统唤醒计时器及硬件支持；关机状态不保证能由任务唤醒。
- 不需要为此修复直接关闭快速启动；Windows 的“重启”采用完整启动路径，恢复连接后也可由无线事件触发。

参考：[唤醒设置](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-waketorun)、[错过后补跑](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable)、[Windows 电源状态](https://learn.microsoft.com/en-us/windows/win32/power/system-power-states)、[S4U 运行账户](https://learn.microsoft.com/en-us/windows/win32/taskschd/principal-logontype)。

## 验证、排障与恢复

先在任务计划程序中手动运行一次，再检查结果和日志：

```powershell
Get-ScheduledTaskInfo -TaskName AutoLogin_SIAS
Get-Content "C:\AutoLogin\auto_login_headless.log" -Tail 20
```

退出码 `0` 且日志出现 `Background login request completed successfully` 表示程序按自身逻辑判断成功；必要时再验证实际联网。随后在方便中断网络时测试断开/重连 `UESTC`、普通关机再开机及重启，等待约 30 秒并查看新日志。安装脚本不会代替这些端到端测试。

若没有启动，打开事件查看器，查看“应用程序和服务日志 → Microsoft → Windows → WLAN-AutoConfig → Operational”是否启用，是否记录了对应 SSID 的 `8001`/`11005`。同时查看 TaskScheduler/Operational，区分事件未产生、任务未启动和程序失败。若出现启动错误，核对 EXE、工作目录和 `.env` 的访问权限及文件是否实际存在本机。

这不是持续联网监控：认证失效但 Wi-Fi 不断开、事件没有被记录/接收、服务器故障持续超过重试次数，都可能需要后续触发或手动处理。每日 04:10 专门处理固定时段重新认证需求。

更新前的 XML 可恢复：在任务计划程序中停用当前任务，保留备份，再用“导入任务”重新导入原 XML；同名冲突时需先删除当前任务。对于本脚本支持的 S4U/InteractiveToken 任务，也可以在管理员 PowerShell 中直接覆盖恢复：

```powershell
Register-ScheduledTask -TaskName AutoLogin_SIAS -Xml (Get-Content -LiteralPath "完整备份路径.xml" -Raw) -Force
```

恢复后检查触发器和下一次运行时间。不要把不同电脑的账户标识直接复制到本机任务中。
