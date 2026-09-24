# AutoLogin SIAS

连接校园网后自动完成 SIAS 认证，也可每天定时重新认证。运行时无需打开浏览器。

**当前版本：v1.2.0 · Windows x64 · 无需安装 Python**

**[下载一键安装包](https://github.com/LeeAstra/autologin-sias/releases/download/v1.2.0/AutoLogin_SIAS_Installer.exe)** · [版本说明](https://github.com/LeeAstra/autologin-sias/releases/tag/v1.2.0) · [使用与排障](docs/USAGE.md)

## 第一次使用，按这 4 步操作

### 1. 连接校园网，准备账号

- 电脑连接本项目适配的 SIAS 校园网，默认 Wi-Fi 名称为 **`UESTC`**。
- 准备好自己的**校园网账号和密码**，不是 Wi-Fi 密码或 Windows 密码。
- 使用你自己的 Windows 管理员账户完成安装。

安装时会发起一次真实认证，需要能访问校园网认证服务器。其他学校或认证系统是否适用，需要单独验证。

### 2. 下载并打开安装包

点击上方“下载一键安装包”，得到：

```text
AutoLogin_SIAS_Installer.exe
```

双击运行。Windows 询问是否允许更改设备时，确认是刚下载的本项目安装包后允许。随后会打开一个**文字输入窗口**。

**安装位置与空间：**程序自动安装到 `%LOCALAPPDATA%\AutoLogin_SIAS`，通常是 C 盘的 `C:\Users\你的用户名\AppData\Local\AutoLogin_SIAS`。程序文件约占 **10 MB**，配置、日志和任务备份另计；下载的安装包另占 **16.32 MB**。即使从 D 盘运行安装包，安装位置也不变，目前没有目录选择功能。成功后可删除下载的安装包，但请保留安装目录。[查看空间明细](docs/USAGE.md#安装位置与磁盘占用)

如果系统要求输入另一个管理员账户的密码，先停止安装，见 [使用指南](docs/USAGE.md)。任务和安装位置与运行安装器的账户有关。

<details>
<summary>从 Releases 页面下载时，应该选哪个文件？</summary>

展开 `Assets`，选择 **`AutoLogin_SIAS_Installer.exe`** 即可。`Source code (zip/tar.gz)` 是源码，不能双击安装。

| 文件 | 用途 |
|---|---|
| `AutoLogin_SIAS_Installer.exe` | 普通用户使用的完整安装包 |
| `AutoLogin_SIAS_Headless.exe` | 已有部署单独更新后台程序时使用 |
| `SHA256SUMS.txt` | 校验下载文件是否完整 |

旧版 `AutoLogin_SIAS_Setup.exe` 的用法见历史文档，不用于本次安装。

</details>

### 3. 输入校园网账号和密码

按窗口提示依次输入，每项输入后按回车：

```text
校园网账号：
校园网密码（不显示）：
```

**输入密码时不会显示文字，也不会显示星号，这是正常现象。** 输入完成后按回车，等待程序验证账号、安装后台程序并配置自动任务。

### 4. 看到“部署完成”，再关闭窗口

成功时会显示：

```text
部署完成！后台认证和自动任务已就绪。可删除下载的安装包。
```

看到这句话后，按回车关闭窗口。以后由 Windows 自动任务运行，无需每天打开安装包。若显示“部署未完成”，请按 [使用与排障指南](docs/USAGE.md) 处理。

## 安装成功后，怎么确认？

1. 按 `Win + R`，输入 `taskschd.msc`，按回车。
2. 在“任务计划程序库”中找到 **`AutoLogin_SIAS`**。
3. 右键选择“运行”，等待任务运行结束后刷新；“上次运行结果”应为 **`0x0`**。

也可查看日志：按 `Win + R`，粘贴下面的路径并回车，打开 `auto_login_headless.log`：

```text
%LOCALAPPDATA%\AutoLogin_SIAS
```

末尾出现 `Background login request completed successfully` 表示程序判断认证成功，再打开网页确认实际联网。上面是安装器默认路径；沿用旧目录的用户应查看任务“操作”中的实际程序位置。

## 以后什么时候会自动运行？

| 场景 | 默认行为 |
|---|---|
| 连接 `UESTC`，产生匹配的无线事件 | 等待约 30 秒后认证 |
| 每天 04:10 | 新建任务会重新认证一次 |
| 电脑正在睡眠 | 不主动唤醒；恢复后允许补跑，可能延迟 |
| 更新已有任务 | 保留原定时计划和电源设置，不一定是默认值 |

它按事件和时间触发，**不会持续检测网络是否掉线**。如果 Wi-Fi 没断开但认证失效，可按上面的步骤手动运行一次任务。

## 常见操作

- **把程序迁移到 D 盘**：[修改安装位置](docs/USAGE.md#修改安装位置)
- **VPN 全局代理挡住认证页**：[让 `2.2.2.3` 走校园网直连](docs/USAGE.md#vpn-全局代理)
- **查看日志、安装失败、升级、停用或卸载**：[使用与排障指南](docs/USAGE.md)
- **修改 Wi-Fi 名称、时间或电源设置**：[自动任务高级配置](docs/USAGE.md#自动任务高级配置)
- **反馈问题**：[提交 Issue](https://github.com/LeeAstra/autologin-sias/issues/new)。请说明版本、操作步骤和错误提示；不要上传密码或 `.env`。

## 适用范围与更多资料

已验证自动化测试、实际 EXE 回归、真实 UESTC 认证及现有计划任务执行。完整安装向导/UAC、全新账户、锁屏和断网重连仍有待补充实机验证，详见 [验证记录](docs/DEVELOPMENT.md#验证记录)。

账号密码保存在本机 `.env` 文件中；门户使用 HTTP 和 RC4 兼容协议。仅使用你有权使用的账号，勿分享配置文件，详见 [安全说明](docs/USAGE.md#账号与配置安全)。

[更新日志](CHANGELOG.md) · [源码构建与发布](docs/DEVELOPMENT.md#构建与发布) · [v1.1 历史教程](https://github.com/LeeAstra/autologin-sias/blob/v1.1.0/README.md) · [MIT 许可证](LICENSE)
