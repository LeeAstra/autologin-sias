# 单次登录诊断版本

直接调用项目现有 `run_login()`，不重写认证协议、不替换安装的 EXE、不修改计划任务。每次手动执行一次正式流程，已认证时跳过登录，保存一个 `results/*.json`。附加的登录前后检查独立使用会话，记录门户资料查询及实际外网探测；这些检查会产生额外请求。

## 两次对比

先停止正在运行的夜间监测，避免它抢先恢复认证。保持同一台电脑连接 UESTC，避免其他网络或 VPN 改变出口。实验会额外提交认证；v1.3.0 两种维护模式可能同时重登，不能只避开旧版 04:10。若需要隔离，先手动暂停正式维护并记录影响，测试结束按[使用指南](../../../docs/USAGE.md#暂停恢复和卸载)恢复。本工具不替你修改任务。

仓库仅发布源码，先按文末说明构建 EXE，或用 `python .\record_login.py` 加相同参数运行。

在本文件夹地址栏输入 `powershell` 并按回车打开终端：

1. 手动在门户注销，确认外网已不可用。不要再在浏览器登录。运行：

   ```powershell
   .\AutoLogin_SIAS_Diagnostic.exe --label offline
   ```

2. 确认第一次执行后外网恢复，保持在线，运行：

   ```powershell
   .\AutoLogin_SIAS_Diagnostic.exe --label already-online
   ```

3. 把 `results` 中这两份 JSON 发给助手分析。不要发送 `.env`。如果显示 `unknown`，它代表状态未确认，不能视为未登录。

默认读取本目录 `.env` 或 `%LOCALAPPDATA%\AutoLogin_SIAS\.env`。自定义安装位置可用 `--env 'D:\AutoLogin_SIAS\.env'`，只读取，不复制配置。

## 记录内容

- 登录前、登录后三种联网状态：online / auth_required / unknown。
- 登录前后分别以新会话访问 `http://2.2.2.3/`，保存每次 HTTP 重定向的地址、状态码、响应头及最终 URL/页面内容。`root_navigation` 保存摘要。
- 最终路径对应的候选认证状态，以及 HTML meta refresh / 内嵌 JavaScript 的跳转地址线索。页面脚本不执行，可能受条件控制的跳转线索不算已验证状态。外部 JS 地址会保留在页面正文中，但不会额外加载。
- `portal_info_state_candidate`、`portal_state_candidate` 是待实测验证的判断；若资料接口与根地址的判断相互矛盾，记录 `portal_evidence_conflict=true`，汇总判断为 unknown。
- 门户 `info.php` 的资料查询响应，用于验证它在两种状态下的差异；不会预先把资料查询成功当作已认证。
- 正式程序先检测、按需登录、登录后确认的请求顺序、URL、表单字段、HTTP 状态、最终 URL、请求/响应头、响应内容和耗时。
- 原登录程序返回码、日志消息、整体认证耗时。`login` 阶段与前后额外探测分别标记。

账号、明文/加密密码、auth_tag、Cookie、令牌及常见个人资料字段会遮蔽。记录不是未脱敏的抓包，也没有底层 TCP 数据；每一跳的 HTTP 重定向详情仅针对新增的根地址探测。原始内容仅用于内存中的协议处理；磁盘记录保存脱敏版本。

此版本仍是手动执行一次登录的诊断工具，不会循环认证或停用原任务。循环监测版见相邻 `login-monitor` 目录；正常在线时只查状态，失效才重登，避免反复认证改变本来要观察的失效规律。已有样本中认证流程约 0.17 秒，但这不代表可以按此间隔持续请求；检测频率还需考虑状态查询耗时及门户限流。

两次测试能判断本次请求和响应是否有差异，以及登录前探测能否区分状态；不能仅凭两次一致响应证明永远不存在可用门户状态接口。登录后立即探测失败也可能是网络放行延迟，需要结合实际联网情况分析。

## 源码与构建

源码运行：`python .\record_login.py --label offline`（Python 3.10+）。构建：`powershell -ExecutionPolicy Bypass -File .\Build.ps1 -Python '实际路径\python.exe'`，需要已安装 PyInstaller。
