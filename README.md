# AutoLogin SIAS

校园网 SIAS 认证自动登录工具。当前稳定发布为 **Headless 1.1**，本分支为 **1.2.0-rc.1 一键部署候选版**：通过 HTTP 请求完成认证，不启动浏览器、不操作桌面，适合 Windows 定时任务和锁屏状态运行。

> [!IMPORTANT]
> 本项目只适用于你有权使用的校园网账号和认证系统。请遵守学校网络管理规定。不要提交 `.env`、账号、密码、Cookie、HAR 或真实 MAC 地址。

## 当前版本

- 推荐源码：[src/auto_login_headless.py](src/auto_login_headless.py)
- 源码版本：`1.2.0-rc.1`；稳定发布：`1.1.0`
- Windows 后台版：`AutoLogin_SIAS_Headless.exe`
- 首次配置向导：`AutoLogin_SIAS_Setup.exe`
- 旧版 GUI 自动化脚本：仅作为历史归档，不建议继续使用

Headless 版本使用标准库实现 HTTP 请求和 RC4 兼容逻辑，不依赖 `requests`、浏览器或 `pyautogui`。

## 快速开始（Windows）

### 候选版：单文件一键部署

运行 `AutoLogin_SIAS_Installer.exe`，允许 Windows 管理员授权，输入校园网账号密码，即可完成后台程序安装、登录验证和自动任务注册。安装前请连接 `UESTC`，使用自己的 Windows 管理员账户，不要用其他账户的凭据提权。

文件安装到 `%LOCALAPPDATA%\AutoLogin_SIAS`，无需手动移动 EXE、运行独立配置向导或粘贴 PowerShell 命令。密码保存在该目录的 `.env`。登录验证失败会恢复原程序和配置；任务安装失败会保留已验证的文件并显示错误，修复原因后可重新运行安装包。

新任务监听 `UESTC` 的 `8001 / 11005` 事件并每天 04:10 执行；更新任务仍保留原时间计划和电源设置。不要删除安装目录；下载的安装包可在成功后删除。安装不会自动启用已关闭的 WLAN 事件日志，遇到该错误请按任务指南启用后重试。

构建单文件安装包（需要 Python 和 PyInstaller）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Installer.ps1
```

产物为 `packaging/dist/AutoLogin_SIAS_Installer.exe`，只需分发这一个文件。下面的双 EXE 方式继续作为手动部署选项。

### 第一步：下载并准备目录

从 [Releases](https://github.com/cloudLee-icy/autologin-sias/releases) 下载：

- `AutoLogin_SIAS_Setup.exe`：首次配置向导；
- `AutoLogin_SIAS_Headless.exe`：真正加入定时任务的后台程序。

把两个文件放到同一个固定目录，例如：

```text
C:\AutoLogin\
├─ AutoLogin_SIAS_Setup.exe
└─ AutoLogin_SIAS_Headless.exe
```

不要把 EXE 放在“下载”临时目录、OneDrive 同步中的经常变动目录或虚拟环境目录中。

### 第二步：运行配置向导

1. 双击 `AutoLogin_SIAS_Setup.exe`；
2. 输入自己的校园网账号；
3. 输入校园网密码（输入时不会显示字符）；
4. 向导在同目录生成 `.env`；
5. 向导会立即发起一次后台登录测试。

测试成功后，目录应类似：

```text
C:\AutoLogin\
├─ AutoLogin_SIAS_Setup.exe
├─ AutoLogin_SIAS_Headless.exe
├─ .env
└─ auto_login_headless.log
```

如果向导提示测试失败，先不要创建定时任务，查看 `auto_login_headless.log` 并确认电脑已连接校园网 Wi‑Fi。

### 第三步：手动运行后台程序

双击无窗口版不会弹出界面。手动测试后，请打开日志确认结果：

```text
Background login request completed successfully
```

也可以在 PowerShell 中测试并查看退出码：

```powershell
cd C:\AutoLogin
.\AutoLogin_SIAS_Headless.exe
$LASTEXITCODE
```

退出码为 `0` 表示本次请求成功。

无参数运行是定时任务模式；配置向导支持 `--setup`，版本检查支持 `--version`，手动测试支持 `--check`。

## Windows 自动任务（一条命令）

同时支持 **连接指定 `UESTC` Wi-Fi 后认证** 和 **每天 04:10 重新认证**。
先完成上面的账号配置及手动测试，再用同一 Windows 账户以管理员身份打开 PowerShell，在仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-AutoLoginTask.ps1 -ExePath "C:\AutoLogin\AutoLogin_SIAS_Headless.exe"
```

请替换为实际 EXE 路径。也可以单独下载 [安装脚本](scripts/Install-AutoLoginTask.ps1)，并替换 `-File` 路径。脚本不会立即运行登录程序。

- 监听 `8001` 或 `11005`，严格筛选事件中的 `SSID = UESTC`，延迟 30 秒执行，补充快速启动/低功耗恢复时可能缺失的 `8001` 事件。
- 新任务每天 04:10 运行；已有任务会先备份，并保留全部原定时触发器，包括旧的一次性触发器。
- 重复触发时不打断已有实例；新任务默认每 5 分钟重试、最多 3 次、运行上限 3 分钟。
- 不新增开机或登录触发；不主动唤醒电脑。已有任务的重试和电源设置不变。

详细的手动配置、XML 筛选、参数、预览、睡眠行为、验证与恢复方法见 **[Windows 自动任务指南](docs/TASK_SCHEDULER.md)**。

## 配置文件

复制 `.env.example` 为 `.env`，填入自己的账号：

```env
WLAN_USER=your_username
WLAN_PWD=your_password
```

程序会优先寻找 EXE 同目录的 `.env`，其次寻找上级目录和当前工作目录。`.env` 永远不要提交到 GitHub。

## 日志和退出码

日志文件：`auto_login_headless.log`。正常成功会包含：

```text
Login response: ... result=True
Jump check: status=200
Background login request completed successfully
```

常见退出码：

| 退出码 | 含义 |
|---:|---|
| 0 | 请求完成并通过成功判断 |
| 2 | 缺少账号或密码 |
| 4 | 认证服务器返回异常 HTTP 状态 |
| 5 | 服务器明确拒绝登录 |
| 6/7 | HTTP 或网络错误 |
| 8 | 无法从响应确认认证成功，按失败处理并允许任务重试 |
| 9 | 未预期错误 |

## 从源码运行和打包

当前后台核心只使用 Python 标准库；Windows 打包需要 PyInstaller：

```powershell
python src/auto_login_headless.py --version
python src/auto_login_headless.py --check
Set-Location packaging
pyinstaller --noconfirm auto_login_headless.spec
pyinstaller --noconfirm auto_login_headless_setup.spec
```

推荐在目标平台分别构建，不能把 Windows EXE 直接当作 Linux/macOS 程序使用。当前发布物面向 Windows x64；Linux、macOS、ARM 架构需要分别测试和打包。

## 安全说明

- 登录门户使用 HTTP，密码按门户要求用 RC4 兼容算法转换；这不是现代安全传输。
- 不要把真实 cURL、HAR、Cookie、日志或 `.env` 上传到仓库。
- 如果账号或密码曾经出现在公开截图、提交或日志中，请及时更换。
- 其他同学可以使用自己的 `.env`，不需要修改源码。

## 历史版本

旧版 v1–v4.4、V30 和图像模板仅保留在开发者本地归档目录，不属于当前发布源码；它们依赖浏览器、前台窗口或 `pyautogui`，锁屏后不可靠。新部署应使用 Headless 1.1。

## 许可证

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
