# AutoLogin SIAS

**当前版本：v1.2.0 · Windows x64 一键部署**

校园网 SIAS 后台认证工具。通过 HTTP 请求完成认证，无需启动浏览器或操作桌面。

## 下载与安装

**[下载 v1.2.0 安装包](https://github.com/LeeAstra/autologin-sias/releases/download/v1.2.0/AutoLogin_SIAS_Installer.exe)** · [版本说明与校验文件](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0)

1. 连接 `UESTC` 校园网 Wi-Fi。
2. 双击 `AutoLogin_SIAS_Installer.exe`，允许 Windows 管理员授权。使用自己的 Windows 管理员账户，不要换用其他账户提权。
3. 输入校园网账号和密码。程序会安装后台 EXE、验证登录，并创建或更新自动任务。
4. 出现“部署完成”后即可关闭窗口。

**普通用户只需要下载安装器这一个文件**，不需要另行下载旧版 `AutoLogin_SIAS_Setup.exe`、手动移动后台 EXE 或粘贴 PowerShell 命令。

默认安装目录：`%LOCALAPPDATA%\AutoLogin_SIAS`。成功后可以删除下载的安装包，但应保留安装目录。

| Release 附件 | 用途 |
|---|---|
| `AutoLogin_SIAS_Installer.exe` | 完整安装入口，内置后台 EXE 和任务脚本 |
| `AutoLogin_SIAS_Headless.exe` | 已有部署或高级用户单独更新后台程序 |
| `SHA256SUMS.txt` | 下载文件的 SHA-256 校验清单 |

## 安装后如何运行

- 连接指定 Wi-Fi：监听 `8001 / 11005` 事件中的 `SSID = UESTC`，延迟 30 秒认证。
- 新建任务：每天 **04:10** 再认证一次；失败后每 5 分钟重试，最多 3 次。
- 更新已有任务：备份 XML，保留原时间计划、账户、重试和电源设置；不会自动补建每日任务。
- 默认不主动唤醒电脑；睡眠期间错过的定时允许恢复后补跑，不保证立即执行。

详细参数、手动管理、睡眠行为和恢复方法见 [自动任务指南](docs/TASK_SCHEDULER.md)。

## 已有用户升级

可以重新运行最新版安装器，重新输入账号密码。安装器使用上述固定目录，验证成功后更新同名 `AutoLogin_SIAS` 任务的程序路径；自定义名称的旧任务需要按任务指南单独处理。只有新任务采用默认时间计划。

若希望保留现有安装位置，可先备份原后台 EXE 和任务 XML，再用本版本的独立后台 EXE 替换原文件，并手动运行任务检查结果。不要在任务运行过程中替换文件。

旧格式 `.env` 继续兼容。新版向导生成的配置带有 `env-format=json-v1` 标记，可保留密码中的空白、引号和反斜杠；不要删除标记。回退旧程序时应同时恢复旧配置。升级不需要混用旧版 Setup。

## 验证与排障

日志位于后台 EXE 同目录的 `auto_login_headless.log`。成功时包含 `Background login request completed successfully`，任务最后运行结果应为 `0`。

| 退出码 | 含义 |
|---:|---|
| 0 | 认证请求通过成功判断 |
| 2 | 缺少账号或密码 |
| 4 | 认证服务器返回异常状态 |
| 5 | 服务器明确拒绝认证 |
| 6 / 7 | HTTP 或网络错误 |
| 8 | 无法从响应确认认证成功 |
| 9 | 未预期错误 |

登录验证失败会恢复安装前的文件；任务安装失败会保留已验证文件并显示原因。若 WLAN 事件日志被关闭，需按任务指南启用后重试。

已验证：18 项 Python 测试、任务 XML、实际 EXE 回归、真实 UESTC 认证和现有计划任务执行。完整安装向导/UAC、全新账户、锁屏和断网重连仍未覆盖全部实机场景；版本发布不代表这些场景已经全部验收。详情见 [验证记录](docs/VALIDATION.md)。

## 开发与历史版本

- [源码构建与发布流程](docs/RELEASE.md)
- [更新日志](CHANGELOG.md)
- [v1.1 旧版双 EXE 部署说明](docs/LEGACY_1.1.md)
- [全部历史 Release](https://github.com/LeeAstra/autologin-sias/releases)

旧版 v1–v4.4、V30 浏览器自动化实现仅作为历史归档；当前发布使用 Headless 后台实现。

## 安全与许可证

仅用于你有权使用的校园网账户。门户使用 HTTP 和 RC4 兼容协议，不是现代安全传输。不要提交 `.env`、账号密码、Cookie、HAR 或真实日志。详见 [安全说明](docs/SECURITY.md)。

采用 [MIT License](LICENSE)。
