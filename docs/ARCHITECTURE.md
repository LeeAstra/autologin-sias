# 三层结构与关键约定

面向维护认证逻辑和平台适配的开发者。运行和测试步骤在[开发指南](DEVELOPMENT.md)，本页解释职责和不能混用的策略。

## 三层分工

```text
src/sias_autologin/
  core/portal.py           HTTP、Cookie、门户地址与请求
  core/authentication.py   RC4、结构化结果与严格文字响应判断
  core/state.py            认证状态查询和判定
  core/service.py          一次认证、提交前保护及恢复确认
  runtime/monitor.py       通用窗口、轮询、提交冷却、运行证据
  platforms/windows/
    network.py            Windows WLAN API 连接核验
    runner.py             模式入口、单实例、平台许可回调
    installer.py          文字安装向导
    deployment.py         文件部署、备份与回滚事务
    tasks.py              任务发现、停止、快照与恢复
    install_lock.py       跨进程安装互斥
  cli.py / config.py       配置、参数、日志及凭据适配
  version.py              唯一版本来源
scripts/windows/           任务 XML 生成、预检、注册与证据读取
scripts/build/             打包及构建来源记录
```

`core` 不读配置、不执行 Windows 命令，只接收凭据、日志及 `PortalClient`。`runtime` 通过注入回调判断网络、查询状态和执行认证；平台决定是否可以运行。CLI 和兼容入口负责文件与环境变量，不将其放进认证核心。

可在已经配置好源码路径的 Python 中只查询状态，不提交凭据：

```python
from sias_autologin.core.portal import PortalClient

state, reason = PortalClient().query_state()
```

这是实际门户请求，不是离线示例。`ensure_authenticated(username, password, client=...)` 返回整数退出码，可能提交认证，不能当作只读查询。

## 认证策略

| 调用场景 | 已认证 | 未知 | 明确需认证 |
|---|---|---|---|
| 默认单次操作 | 跳过提交 | 保留旧行为，尝试认证 | 尝试认证 |
| 维护：`require_auth_required=True` | 跳过提交 | 等待 | 尝试认证 |
| 配置验证：`validate_credentials=True` | 仍验证凭据 | 仍验证凭据 | 验证凭据 |

维护的第二次查询同样受策略约束，不能把第一次需认证当作持续有效。`before_auth` 在门户页面请求及凭据 POST 前确认平台许可；夜间窗口和 UESTC 必须仍成立。已开始请求允许完成。结构化响应优先，文字仅匹配明确完整格式；否定、冲突和含糊响应不能报告验证成功。提交结果成功后还要确认门户状态。

普通运行优先非空环境凭据；独立 `--setup` 和安装器强制验证保存配置，忽略旧环境覆盖。配置序列化支持旧 `.env` 和 `json-v1`，编码不等于加密。

## 循环与网络许可

`LoginResult(code, submitted, confirmed)` 区分退出码、真实提交及确认结果。维护回调必须返回该类型，不能凭整数猜测是否提交。实际提交后设至少 15 秒的冷却；未提交维持原检测周期。等待使用休眠，日志以状态变化、认证结果和退出为主。

Windows 每次重新查询 WLAN，不缓存连接状态。API 绑定来自 System32，固定 ABI 字段；接口/查询内存在 finally 释放，句柄关闭。任一无线接口明确连接 UESTC 可提供目标证据；无目标且仍有无法确认接口时返回 `network_unverified`。明确离开返回 `wrong_network`，由循环正常退出。

后台维护与独立实验工具用途不同：正式循环不主动防休眠，实验监测有自己的睡眠和采样策略。不能用实验参数描述正式维护模式。

## 安装事务与证据

安装锁在读取旧状态前取得；旧任务预检复用任务脚本 `-ExportOnly`，先于停止任务和替换文件。文件备份及完整任务 XML 用于失败恢复；停止时核对同账户、同路径残留进程，不按名称结束其他程序。原位安装替换目标文件；迁移成功保留旧目录文件，启动请求不是清理依据。

现代向导选择维护模式会更新对应触发器及执行时限，保留电源条件。底层 `mode=None` 和任务脚本不传 `-Mode` 的旧单次接口只为兼容，不能将其默认 04:10 或旧恢复语义当作完整安装器行为。

每轮结构化事件用 UUID `run_id` 和带时区时间关联。验收脚本只匹配最近任务开始时间、模式及完整边界；缺失、重复跳过或异常结束不能借用历史成功。早晨的新触发可能覆盖“当前轮次”选择，分析整夜须明确选取历史轮次并保留其完整边界。[最终验收](releases/v1.3.0-acceptance.md)。
