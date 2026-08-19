# AutoLogin SIAS

校园网 SIAS 认证自动登录工具。当前推荐版本是 **Headless 1.1**：通过 HTTP 请求完成认证，不启动浏览器、不操作桌面，适合 Windows 定时任务和锁屏状态运行。

> [!IMPORTANT]
> 本项目只适用于你有权使用的校园网账号和认证系统。请遵守学校网络管理规定。不要提交 `.env`、账号、密码、Cookie、HAR 或真实 MAC 地址。

## 当前版本

- 推荐源码：[src/auto_login_headless.py](src/auto_login_headless.py)
- 当前版本：`1.1.0`
- Windows 后台版：`AutoLogin_SIAS_Headless.exe`
- 首次配置向导：`AutoLogin_SIAS_Setup.exe`
- 旧版 GUI 自动化脚本：仅作为历史归档，不建议继续使用

Headless 版本使用标准库实现 HTTP 请求和 RC4 兼容逻辑，不依赖 `requests`、浏览器或 `pyautogui`。

## 快速开始（Windows）

1. 从 GitHub Releases 下载两个 EXE，并放到同一个目录。
2. 双击 `AutoLogin_SIAS_Setup.exe`。
3. 输入自己的校园网账号和密码。密码不会回显。
4. 向导会在 EXE 同目录创建 `.env`，并立即测试登录。
5. 在任务计划程序中使用 `AutoLogin_SIAS_Headless.exe`。

推荐任务操作：

```text
程序或脚本：D:\AutoLogin\AutoLogin_SIAS_Headless.exe
添加参数：留空
起始于：D:\AutoLogin
```

无参数运行是定时任务模式；配置向导支持 `--setup`，版本检查支持 `--version`，手动测试支持 `--check`。

## 配置文件

复制 `.env.example` 为 `.env`，填入自己的账号：

```env
WLAN_USER=your_username
WLAN_PWD=your_password
```

程序会优先寻找 EXE 同目录的 `.env`，其次寻找上级目录和当前工作目录。`.env` 永远不要提交到 GitHub。

## 任务计划程序

### 固定时间

使用“仅在用户登录时运行”或“不管用户是否登录都要运行”均可。Headless 版本不依赖桌面，锁屏后仍可运行。

### 连接 UESTC 时触发

可以监听：

```text
日志：Microsoft-Windows-WLAN-AutoConfig/Operational
事件 ID：8001
```

建议延迟 30 秒，并在任务设置中取消“只有在以下网络连接可用时才启动”，避免校园网尚未认证时条件本身阻止任务启动。SSID 精确过滤可能因 Windows 版本差异而不同；必要时只监听 8001，再由程序执行登录。

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
