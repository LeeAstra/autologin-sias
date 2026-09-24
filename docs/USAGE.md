# 使用与排障指南

[返回安装教程](../README.md) · [下载 v1.2.0](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0) · [修改安装位置](#修改安装位置) · [VPN 全局代理](#vpn-全局代理) · [任务高级配置](#自动任务高级配置)

本页适用于 v1.2.0。先按 README 完成安装，遇到问题时查阅对应部分。

## 找到安装目录和日志

通过安装器部署的用户，按 `Win + R`，输入以下路径，按回车：

```text
%LOCALAPPDATA%\AutoLogin_SIAS
```

这个写法会自动定位到当前 Windows 账户的本地文件夹，不需要把 `%LOCALAPPDATA%` 改成用户名。默认目录中有：

| 文件 | 用途 |
|---|---|
| `AutoLogin_SIAS_Headless.exe` | 静默执行认证的后台程序 |
| `Install-AutoLoginTask.ps1` | 安装器调用的任务配置脚本 |
| `.env` | 本机账号密码配置，勿上传或分享 |
| `auto_login_headless.log` | 认证记录，排查问题时查看末尾的新记录 |

旧版用户可能仍在自定义目录运行。按 `Win + R` → 输入 `taskschd.msc` → 任务计划程序库 → 双击 `AutoLogin_SIAS` → “操作”，查看实际 EXE 路径，再去那个目录找日志。

日志包含 `Background login request completed successfully` 表示本次请求通过程序的成功判断；还应通过浏览网页确认实际联网。

## 安装位置与磁盘占用

v1.2.0 的 `AutoLogin_SIAS_Installer.exe` 固定安装到 `%LOCALAPPDATA%\AutoLogin_SIAS`，通常对应 **`C:\Users\你的用户名\AppData\Local\AutoLogin_SIAS`**。若系统迁移过用户目录，则以 `%LOCALAPPDATA%` 的实际位置为准，并非硬编码为 C 盘。

**把安装包放到 D 盘不会改变安装目录**，安装器目前没有目录选择功能。要把后台程序迁到其他盘，请按下方的 [修改安装位置](#修改安装位置) 操作。

以下按当前 v1.2.0 发布文件大小统计，MB 使用十进制；Windows 显示值及磁盘实际分配空间可能略有不同。

| 项目 | 大小或占用说明 |
|---|---|
| 安装后的后台 EXE 与任务脚本 | 合计 9,996,648 字节，约 **10 MB** |
| 下载的安装包 | 16,317,941 字节，约 **16.32 MB**；保存在下载位置，安装成功后可删除 |
| `.env` 配置 | 少量文本，大小随账号密码长度变化 |
| 认证日志 | 正常轮转约 **1.5 MiB**：当前文件约 512 KiB，另保留两份轮转日志 |
| `TaskBackups` 任务 XML 备份 | 更新已有任务时生成，每次一份；不自动清理，长期占用会增长 |
| 安装或运行期间的临时文件 | 单文件 EXE 还需临时解压空间，未计入上面的约 10 MB 程序占用 |

如果安装包也保存在 C 盘，那么程序与安装包合计约 **26.32 MB**，再加配置、日志、任务备份及运行时临时文件。删除下载的安装包不会卸载已安装程序；删除安装目录会影响任务运行。

## 修改安装位置

v1.2.0 安装器不能在安装时选择目录。若要放到 D 盘，可先完成默认安装，再迁移后台程序和现有任务。下面以本机固定目录 `D:\AutoLogin` 为例；请选择自己有权限、不会同步到云端的目录。`.env` 含明文账号密码，复制前请确认新目录仅允许你信任的账户读取。

1. 在任务计划程序中找到 `AutoLogin_SIAS`，先右键“禁用”；若正在运行，等它结束。记下“操作”中的旧程序路径。以下命令假设它是安装器默认目录；如果实际路径不同，请用实际目录替换 `$source`。
2. 以当前 Windows 账户打开 PowerShell，复制后台 EXE、配置和任务脚本。不要只移动下载文件夹里的安装包。

   ```powershell
   $source = Join-Path $env:LOCALAPPDATA 'AutoLogin_SIAS'
   $destination = 'D:\AutoLogin'
   New-Item -ItemType Directory -Path $destination -Force | Out-Null
   foreach ($name in 'AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1', '.env') {
       Copy-Item -LiteralPath (Join-Path $source $name) -Destination $destination -Force
   }
   ```

3. 先测试新目录里的程序。以下命令会进行一次真实认证；退出码应为 `0`，并可在新目录查看日志。

   ```powershell
   $check = Start-Process -FilePath 'D:\AutoLogin\AutoLogin_SIAS_Headless.exe' -ArgumentList '--check' -WorkingDirectory 'D:\AutoLogin' -WindowStyle Hidden -Wait -PassThru
   $check.ExitCode
   ```

4. 用**同一个 Windows 账户**以管理员身份打开 PowerShell，更新已有任务的程序路径。脚本会先备份旧任务 XML，并保留已有的时间触发器、账户及电源设置。第一步禁用的任务仍需在下一步手动启用。

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\AutoLogin\Install-AutoLoginTask.ps1' -ExePath 'D:\AutoLogin\AutoLogin_SIAS_Headless.exe'
   ```

5. 回到任务计划程序，检查“操作”里的程序与“起始于”都指向 `D:\AutoLogin`，启用任务，右键“运行”并确认最后结果为 `0x0`、新目录日志出现成功记录。确认后再清理旧目录中的旧 EXE 和旧 `.env`；先保留 `TaskBackups` 里的备份 XML 以便恢复。

这会把约 10 MB 的后台程序移到 D 盘。任务更新脚本仍在 `%LOCALAPPDATA%\AutoLogin_SIAS\TaskBackups` 保存少量 XML 备份。以后若再次运行**一键安装器**，它仍会安装到默认位置，并把同名任务改回该位置；保留 D 盘布局时，请按本节方式更新。

## 安装时遇到问题

| 看到的情况 | 怎么处理 |
|---|---|
| 输入密码后窗口没有出现字符或星号 | 这是隐藏密码输入，正常输入完后按回车即可 |
| 提示“登录验证失败” | 确认连接了适配的校园网，检查校园网账号密码，并查看末尾日志；修复原因后重新运行安装包 |
| 提示“登录已验证，但自动任务安装失败” | 文件已保留，查看窗口中更早的具体错误；按下方说明排查账户、事件日志或旧任务配置后重试 |
| 提示 `WLAN event log is disabled` | 按下一节启用 WLAN 事件日志后重新安装 |
| Windows 授权窗口要求另一个管理员账户的密码 | 先取消。当前安装方式应使用你自己的管理员账户；标准账户请向设备管理员确认部署方式，避免装到别人的账户下 |
| 安装包被系统或安全软件拦截 | 核对是否来自本仓库的 Release，可按本页方法检查 SHA-256；保留具体提示供排查，不需要关闭全局防护 |

登录验证失败或取消时，安装器会尝试恢复此次更改的程序和配置；任务安装失败会保留已验证文件。只有出现“部署完成”才表示完整部署流程成功。

### 启用 WLAN 事件日志

1. 按 `Win + R`，输入 `eventvwr.msc`，按回车。
2. 展开“应用程序和服务日志 → Microsoft → Windows → WLAN-AutoConfig”。
3. 右键 `Operational`，若菜单显示“启用日志”，点击它；若显示“禁用日志”，则已经启用。
4. 若系统要求权限，使用自己的管理员账户完成，然后重新运行安装包。

安装器不会自动启用已关闭的事件日志。

### 旧任务不支持直接更新

以下情况会要求手动处理：存在多个 WLAN 触发器、旧操作带有参数，或运行账户采用脚本不支持的登录方式。

打开任务计划程序，先导出该任务，再对照 [高级指南](#自动任务高级配置) 检查。不要为了跳过错误而直接删除原任务，否则可能丢失自定义计划或账户设置。

## 安装后没有自动联网

先检查电脑连接的是否为 `UESTC`，然后在任务计划程序中右键 `AutoLogin_SIAS` →“运行”，等待结束后刷新。这样可以区分认证程序失败和自动触发没有发生。

- **手动运行也失败**：查看实际程序目录下的日志和上次运行结果。
- **手动运行成功，但自动运行没发生**：检查无线事件日志、任务触发器和电源条件，详见高级指南。
- **Wi-Fi 仍连接，但认证失效**：程序不是持续联网监控器，可能需要手动运行任务或等待下一次定时触发。
- **04:10 时电脑睡眠或关机**：默认不会主动唤醒；睡眠恢复后允许补跑，不能保证立即执行。
- **双击后台 EXE 没窗口**：后台程序就是静默运行的，请看日志；输入账号使用的是安装包。

### 退出码参考

这些是后台程序的退出码。Windows 任务启动失败可能显示其他系统错误码，不能一概当作账号错误。

| 退出码 | 含义 |
|---:|---|
| 0 | 认证请求通过成功判断，任务界面通常显示 `0x0` |
| 2 | 缺少账号或密码 |
| 4 | 认证服务器返回异常状态 |
| 5 | 服务器明确拒绝认证 |
| 6 / 7 | HTTP 或网络错误 |
| 8 | 无法从响应确认认证成功 |
| 9 | 未预期错误 |

## VPN 全局代理

认证门户地址是 **`http://2.2.2.3`**。有些 VPN 的全局代理或全局隧道会把发往该地址的请求带离校园网，导致浏览器打不开认证页、安装器验证失败，或自动任务不能认证。

1. 保持连接 `UESTC`，暂时关闭 VPN，再访问 `http://2.2.2.3` 并运行一次认证。如果恢复正常，问题通常与 VPN 的代理或路由设置有关。
2. 想保持 VPN 开启时，在所用 VPN 软件中查找“分流”“绕过代理”“直连”“排除路由”等设置，让 **`2.2.2.3`**（若规则要求网段，填 `2.2.2.3/32`）通过校园网直连。若软件分别设置**系统代理**和**全局/TUN 隧道**，两处都需要检查；只改浏览器代理不一定能影响后台程序。
3. 保存设置后，在 VPN 开启的状态下重新访问 `http://2.2.2.3`，并在任务计划程序中手动运行 `AutoLogin_SIAS`；确认结果为 `0x0`、日志出现成功记录，再验证实际联网。若软件没有直连规则，使用本工具认证时先关闭 VPN。

本程序通过 Python 的网络库发起请求，可能读取系统或环境代理；全局 VPN 也可能改变系统路由。不同软件的菜单名称不同，按实际界面配置即可。原理参考 [Python 代理说明](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler) 和 [Windows VPN 路由说明](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/vpn/vpn-routing)。

## 升级或修改账号密码

**默认安装方式**：重新运行最新版安装器，输入新的账号密码。安装器会验证认证并更新同名任务，已有定时计划和电源设置保留。

安装器始终使用 `%LOCALAPPDATA%\AutoLogin_SIAS`。若此前在别的目录部署，它会将同名任务的程序路径更新到这个目录；旧目录不会自动删除。先确认新任务运行成功，再处理旧目录。

**保留自定义目录**：先备份原 EXE、配置和任务 XML，确认任务未运行，再将本版本的独立后台 EXE 放到原程序位置，手动运行任务验证。已有配置可继续使用。

**自定义任务名**：安装器默认处理 `AutoLogin_SIAS`；其他名称不会自动更新，应按高级指南使用任务脚本的 `-TaskName` 参数处理，避免多个任务重复认证。

新向导生成的 `.env` 带有 `env-format=json-v1` 标记，保留密码中的空白、引号和反斜杠。不要删除标记。旧格式仍可读取；若回退旧程序，应同时恢复旧配置。

## 暂停或卸载

- **暂停自动认证**：打开任务计划程序，右键 `AutoLogin_SIAS` →“禁用”。需要恢复时选择“启用”。
- **卸载**：先禁用任务，若正在运行则结束它；确认任务的程序路径，再删除该任务和你确认属于本工具的安装目录。配置和日志会随目录一起删除，按需先自行备份。安装器没有单独的卸载向导。
- 下载到“下载”文件夹里的安装包可在成功部署后删除；它与实际安装目录是两个位置。

## 可选：校验下载文件

从同一个 [v1.2.0 Release](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0) 下载 `SHA256SUMS.txt`。在下载目录打开 PowerShell，执行：

```powershell
Get-FileHash -LiteralPath .\AutoLogin_SIAS_Installer.exe -Algorithm SHA256
```

把 `Hash` 与清单中同名文件前的一整串字符对比；大小写不影响比较。应完全一致。不要拿 RC 版本的清单校验正式版本。
## 自动任务高级配置

以下内容用于更改 Wi-Fi 名称、触发时间、重试和电源设置。安装器部署成功后，不需要再运行一次任务脚本。现有任务的时间计划会保留，更新前会备份 XML。

### 手动安装或更新任务

v1.2.0 单文件安装包 `AutoLogin_SIAS_Installer.exe` 已整合下述脚本，完成账号输入和登录验证后会自动调用，普通用户无需再手动执行命令。[下载当前版本](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0)。它将后台程序安装到 `%LOCALAPPDATA%\AutoLogin_SIAS`；新任务与已有任务的处理规则和下文一致。以下内容用于高级手动管理。

先确认已有自己的 `.env`，且手动运行后台 EXE 能认证成功；新版安装器会完成配置。把 EXE 和配置放在固定、已下载到本机的目录中。下载仓库中的 [Install-AutoLoginTask.ps1](../scripts/Install-AutoLoginTask.ps1)，或使用仓库内的副本。

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

### 手动配置

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

### 睡眠、关机与快速启动

- 仅锁屏或关屏、系统仍在运行时，可以按时执行。
- 默认不唤醒：04:10 处于睡眠或休眠时不会为本任务主动醒来；恢复后允许补跑，但不保证立即执行。
- 若确实需要 04:10 唤醒，手动勾选“唤醒计算机运行此任务”，并核对系统唤醒计时器及硬件支持；关机状态不保证能由任务唤醒。
- 不需要为此修复直接关闭快速启动；Windows 的“重启”采用完整启动路径，恢复连接后也可由无线事件触发。

参考：[唤醒设置](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-waketorun)、[错过后补跑](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable)、[Windows 电源状态](https://learn.microsoft.com/en-us/windows/win32/power/system-power-states)、[S4U 运行账户](https://learn.microsoft.com/en-us/windows/win32/taskschd/principal-logontype)。

### 验证、排障与恢复

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

## 账号与配置安全

- `.env` 保存的是本机账号密码，**文件内容未加密**。JSON 字符串编码只是为了完整保存字符，不是加密。
- 不要把 `.env`、整个安装目录、账号密码或原始抓包上传到 GitHub，也不要放进公开网盘链接。
- 门户使用 HTTP 和 RC4 兼容协议；这符合当前门户的认证方式，不代表现代安全传输。仅使用自己有权使用的账户和网络。
- 反馈问题只提供已去掉敏感内容的错误提示或相关日志片段；不要公开 Cookie、真实 MAC 地址或 HAR 文件。

## 反馈问题时提供什么？

到 [Issues](https://github.com/LeeAstra/autologin-sias/issues/new) 说明：使用的版本和 EXE 文件名、Windows 版本、发生问题的步骤、窗口错误或任务结果，以及是否能手动运行成功。

如需日志，只提供去掉敏感内容的相关片段。不要上传 `.env`、账号密码、真实 MAC 地址或原始抓包文件。
