# v1.1 历史部署说明

本页仅适用于旧版 v1.1.0。新安装请使用 [v1.2.0 单文件安装包](../README.md)，不需要下载旧版 Setup EXE。旧版本保留用于历史追溯，不与新版配套使用。

### 第一步：下载并准备目录

从 [Releases](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.1.0) 下载：

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


旧任务的高级配置见 [任务指南](TASK_SCHEDULER.md)。新格式配置不能交给旧版程序读取，回退时应同时恢复匹配的旧配置。
