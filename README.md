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
\.\AutoLogin_SIAS_Headless.exe
$LASTEXITCODE
```

退出码为 `0` 表示本次请求成功。

无参数运行是定时任务模式；配置向导支持 `--setup`，版本检查支持 `--version`，手动测试支持 `--check`。

## 推荐设置：Windows 定时任务

下面是最稳妥的固定时间配置方式。

### 创建任务

1. 按 `Win + R`，输入 `taskschd.msc`，回车；
2. 右侧点击“创建任务”，不要只用“创建基本任务”；
3. “常规”页填写名称，例如 `AutoLogin_SIAS`；
4. 选择“仅在用户登录时运行”或“不管用户是否登录都要运行”；
5. 如果选择后者，Windows 会要求输入一次 Windows 账户密码，这是系统任务凭据，不是校园网密码。

### 设置操作（最重要）

在“操作”页点击“新建”，填写：

```text
程序或脚本：C:\AutoLogin\AutoLogin_SIAS_Headless.exe
添加参数：留空
起始于：C:\AutoLogin
```

“起始于”必须填写 EXE 所在目录。不要填写 `cmd.exe`、`cmd /k`、PowerShell、`.bat` 或旧版 GUI 程序。

### 设置触发器

固定时间测试可以这样设置：

1. “触发器”→“新建”；
2. 选择“按计划”；
3. 设置“每天”或“登录时”；
4. 先设置为几分钟后的时间进行测试；
5. 勾选“已启用”；
6. 保存任务后，右键任务选择“运行”进行立即测试。

建议先手动运行确认成功，再设置每天定时。

### 设置条件

建议取消以下限制：

```text
□ 只有在计算机使用交流电源时才启动此任务
□ 只有在以下网络连接可用时才启动
```

尤其不要要求“UESTC 网络可用”。校园网尚未认证时，Windows 可能认为该网络条件还不可用，反而阻止登录程序启动。

### 设置规则

在“设置”页建议：

```text
☑ 允许按需运行任务
☑ 如果错过计划开始时间，立即启动任务
☑ 如果任务运行时间超过：2 分钟，则停止任务
如果任务已经运行：停止现有实例
```

当前程序正常只需几秒完成。设置 2 分钟超时可以避免网络异常时任务长期显示“正在运行”。

### 锁屏时是否能运行

Headless 版本不启动 Edge、不使用鼠标键盘，因此用户已登录但电脑处于锁屏状态时仍可以运行。旧版 `auto_login_v4.4.py` 依赖前台窗口，不适合锁屏运行。

## 推荐设置：连接 UESTC Wi‑Fi 时触发

如果希望每次连接校园网后自动执行，而不是固定时间执行，可以增加“发生事件时”触发器：

1. 在任务属性打开“触发器”→“新建”；
2. “开始任务”选择“发生事件时”；
3. 选择“自定义”→“新建事件筛选器”；
4. 日志选择：`Microsoft-Windows-WLAN-AutoConfig/Operational`；
5. 事件 ID 填：`8001`；
6. 高级设置中延迟 `30 秒`；
7. 保存任务。

事件 8001 表示无线网络连接成功。不同 Windows 版本对 SSID 精确筛选的界面可能不同；如果无法只筛选 `UESTC`，先只监听事件 8001 即可。不要在任务“条件”页再次要求网络连接为 UESTC，否则可能阻止任务启动。

如果网络刚连接时认证入口还没准备好，可以在触发器中启用重复运行：每隔 5 分钟重复，持续 15 分钟；任务设置中的“如果任务已经运行”选择“停止现有实例”。

## 配置文件

复制 `.env.example` 为 `.env`，填入自己的账号：

```env
WLAN_USER=your_username
WLAN_PWD=your_password
```

程序会优先寻找 EXE 同目录的 `.env`，其次寻找上级目录和当前工作目录。`.env` 永远不要提交到 GitHub。

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
