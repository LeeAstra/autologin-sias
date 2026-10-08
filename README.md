# AutoLogin SIAS

连接 UESTC 后检测 SIAS 认证状态，仅明确需要认证时重新登录。认证核心、通用维护循环和 Windows 平台适配分层，运行安装包无需 Python。

**v1.3.0 · Windows x64**

[下载完整安装器](https://github.com/LeeAstra/autologin-sias/releases/download/v1.3.0/AutoLogin_SIAS_Installer.exe) · [Release](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.3.0) · [安装、升级与恢复](docs/releases/v1.3.0.md) · [文档索引](docs/README.md)

正式发布状态以 Release 页面为准。[实机验收记录](docs/releases/v1.3.0-acceptance.md)记录覆盖范围与限制。

## 安装

1. 连接 UESTC，使用自己的 Windows 管理员账户打开安装器并允许 UAC；不要换另一个管理员账户提权。
2. 输入校园网凭据，选择安装目录。默认 `%LOCALAPPDATA%\AutoLogin_SIAS`，可以选择其他本地目录。密码输入不显示文字。
3. 选择维护模式：默认 **② 夜间维护**，每天 02:55～03:15 每 5 秒检测；**① UESTC 持续维护**每 30 秒检测，明确离开 UESTC 后退出。
4. 确认安装。安装会实际提交本次保存的凭据验证，已在线也不能替代密码验证。部署完成后核对计划任务的执行路径和模式。

任务启动请求成功不代表维护已运行。夜间模式在窗口外正常退出；持续模式运行中不要求上次结果为 0。使用 [验收采集步骤](docs/RELEASE-ACCEPTANCE.md)检查本轮运行证据。

## 升级与恢复

使用完整安装器原位升级或更换目录。安装器先检查旧任务兼容性，再停止旧维护进程并备份文件和任务 XML；失败时尝试恢复。迁移后保留旧目录文件，确认新目录实际工作后由用户处理，避免只因启动命令成功就删除旧文件。不要手动运行旧目录程序。

仅替换后台 EXE 不会更新任务或切换维护模式。详细备份位置、环境变量兼容规则和恢复步骤见 [版本指南](docs/releases/v1.3.0.md)。

## 运行限制

不修改既有任务电源条件，不自动唤醒电脑；夜间实验需要保持唤醒并连接 UESTC。未知认证或 WLAN 状态不提交登录，实际认证失败后至少间隔 15 秒重试。安装包未签名，其他学校的认证接口需要单独适配。

下载文件包括完整安装器、后台 EXE、SHA256SUMS.txt 和 BUILD-INFO.json；普通用户使用完整安装器。源码压缩包不能直接安装。

独立夜间实验放在 [tools/experiments](tools/experiments/README.md)，不随安装包部署，也不修改正式任务。旧版操作参考 [历史版本](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0)。

## 常见操作

- **把程序迁移到 D 盘**：[安装与迁移](docs/releases/v1.3.0.md)
- **VPN 全局代理挡住认证页**：[让 `2.2.2.3` 走校园网直连](docs/USAGE.md#vpn-全局代理)
- **查看日志、安装失败、升级与恢复**：[版本指南](docs/releases/v1.3.0.md)；旧版停用或卸载见[历史使用指南](docs/USAGE.md)
- **修改 Wi-Fi 名称、时间或电源设置**：[自动任务高级配置](docs/USAGE.md#自动任务高级配置)
- **反馈问题**：[提交 Issue](https://github.com/LeeAstra/autologin-sias/issues/new)。请说明版本、操作步骤和错误提示；不要上传密码或 `.env`。

## 适用范围与更多资料

已验证自动化测试、实际 EXE 回归、真实 UESTC 认证及现有计划任务执行。本机升级、迁移运行、断网重连、睡眠恢复和自然登出重登已验证；全新账户、锁屏及多无线网卡仍需独立实机覆盖，详见 [实机验收记录](docs/releases/v1.3.0-acceptance.md)。

账号密码保存在本机 `.env` 文件中；门户使用 HTTP 和 RC4 兼容协议。仅使用你有权使用的账号，勿分享配置文件，详见 [安全说明](docs/USAGE.md#账号与配置安全)。

[代码结构与跨平台开发](docs/ARCHITECTURE.md) · [更新日志](CHANGELOG.md) · [源码构建与发布](docs/DEVELOPMENT.md#构建与发布) · [v1.1 历史教程](https://github.com/LeeAstra/autologin-sias/blob/v1.1.0/README.md) · [MIT 许可证](LICENSE)
