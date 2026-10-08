# AutoLogin SIAS

为连接 **UESTC** 的 Windows 电脑自动维护 SIAS 校园网认证。已经在线时只检测；明确需要认证时才提交登录。适合希望电脑在校园网认证失效后自动重登的用户。

**当前正式版：[v1.3.0](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.3.0)** · Windows x64 · 安装包无需 Python

## 下载哪个文件？

**普通用户下载 [AutoLogin_SIAS_Installer.exe（完整安装器）](https://github.com/LeeAstra/autologin-sias/releases/download/v1.3.0/AutoLogin_SIAS_Installer.exe)。**

| 文件 | 用途 |
|---|---|
| `AutoLogin_SIAS_Installer.exe` | 安装程序、配置凭据、创建或更新自动任务；首次安装和升级都用它 |
| `AutoLogin_SIAS_Headless.exe` | 无窗口后台程序；单独下载不会安装任务，也不会完成交互配置 |
| `Source code (zip / tar.gz)` | 开发者使用的源码压缩包，不能双击安装 |
| `SHA256SUMS.txt`、`BUILD-INFO.json` | 校验下载文件、查看构建来源；[校验步骤](docs/MAINTENANCE.md#校验下载文件) |

默认 Wi-Fi 名称为 `UESTC`，认证接口为 `http://2.2.2.3`。仅验证了本项目对应的 SIAS 协议，不是通用校园网登录器。本轮实机为 Windows 11 x64；其他系统或网络需分别验证。

## 选择哪种模式？

| 安装选项 | 检测周期 | 运行范围 | 适合谁 |
|---|---|---|---|
| ① UESTC 持续维护 | 每轮检测后等待 30 秒 | 连接 UESTC 时维护；明确离开后退出 | 希望全天维护的用户 |
| **② 夜间时段维护（默认）** | 每轮检测后等待 5 秒 | 每天本地时间 02:55～03:15 | 只希望在该时段维护的用户 |

**电脑必须保持唤醒并连接 UESTC。** 程序不自动唤醒，不主动连接 Wi-Fi，也不改变原有任务电源条件。夜间模式在时段外会正常退出。

“五秒检测”是每轮等待间隔，**不保证五秒内恢复网络**：检测和请求耗时、认证服务器响应及失败重试都会影响恢复时间。实际提交后至少等待 15 秒才能再次提交；未知状态先等待。完整规则见[使用指南](docs/USAGE.md#运行条件与触发方式)。

## 第一次安装

准备自己的校园网账号密码，先连接 UESTC。使用自己的 Windows 管理员账户；Windows 的管理员权限提示（UAC）若要求换另一账户提权，先停止安装并[反馈账户环境](docs/TROUBLESHOOTING.md#反馈问题)。

1. 双击完整安装器，核对文件来源后允许 Windows 的权限提示。窗口标题内容包含 `AutoLogin SIAS 1.3.0 一键部署`。
2. 在“安装目录”提示中按回车使用默认位置，或输入本地绝对路径。
3. 在“选择模式 [1/2，默认2]”中输入 `1` 或 `2`；直接回车选择夜间模式。
4. 输入校园网账号和密码；密码不显示文字或星号是正常现象。发现旧配置时会询问是否保留。
5. 核对目录和模式，在“确认安装？[Y/n]”中按回车继续。安装会验证凭据并更新任务；看到“部署完成”后按回车关闭窗口。

更多操作：[升级、改密码、切换模式、迁移和卸载](docs/USAGE.md)。火绒提示的用途与核查方法见[故障排查](docs/TROUBLESHOOTING.md#火绒或其他行为防护提示)。

## 怎样确认在工作？

“部署完成”说明任务已更新并请求启动，不能单独证明网络恢复。按三个层次检查：

1. **任务已注册：** 按 `Win + R`，输入 `taskschd.msc`；在“任务计划程序库”找到 `AutoLogin_SIAS`。打开“属性 → 操作”，确认程序路径及 `--maintain night` 或 `--maintain continuous`。
2. **程序实际运行：** 持续模式在 UESTC 下通常显示“正在运行”；夜间模式在时段外显示“就绪”并返回 `0x0` 属正常情况。到实际安装目录查看 `auto_login_headless.log` 中本轮 `start` 和状态记录。
3. **认证恢复：** 本轮日志应出现 `auth_required`、真实提交及 `confirmed=true` 的 `login_result`。再打开常用网页检查外网；门户认证成功不等于外网一定可用。

一直在线时没有认证提交是正常现象。详细判断、只读状态采集和反馈模板见[故障排查](docs/TROUBLESHOOTING.md#确认任务和本轮运行)。

## 其他入口

- [使用指南](docs/USAGE.md)：安装及日常维护。
- [故障排查](docs/TROUBLESHOOTING.md)：安装失败、未联网及安全软件提示。
- [开发指南](docs/DEVELOPMENT.md)：源码入口、三层结构、测试及构建。
- [贡献与发布](CONTRIBUTING.md)：提交流程；[维护与发布指南](docs/MAINTENANCE.md)说明来源与校验。
- [历史与实验](docs/history/README.md)：旧版说明、独立实验、最终验收及历史测量。

凭据保存在本机 `.env`，不是加密存储。不要上传真实配置、密码、Cookie 或整个安装目录。[配置与隐私说明](docs/USAGE.md#配置与隐私)。项目采用 [MIT 许可证](LICENSE)。
