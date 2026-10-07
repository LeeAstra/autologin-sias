# 维护与验证

当前源码与最新预发布为 **v1.3.0-rc.4**；稳定 Latest 仍为 **v1.2.0**。唯一版本来源是 `src/sias_autologin/version.py`。不同版本安装器和后台EXE不得混用。

代码组织见 [三层架构](ARCHITECTURE.md)，安装与模式选择见 [rc.4指南](releases/v1.3.0-rc.4.md)，全部入口见 [文档索引](README.md)。

## 构建与发布

使用 Windows x64 / Python 3.13，安装 `requirements-build.txt` 后运行：

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tools/experiments/login-diagnostics -v
python -m unittest discover -s tools/experiments/login-monitor -v
powershell -NoProfile -ExecutionPolicy Bypass -File tests/Test-TaskPreview.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tests/Test-AcceptanceEvidence.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build/Build-Installer.ps1
python tests/check_task_commands.py
python tests/check_task_recovery.py
python tests/check_installer_lock.py
python tests/check_bundle.py
python tests/check_live_wlan.py
python tests/check_frozen_login.py
```

产物位于 `packaging/dist/`：安装器EXE、后台EXE及SHA256SUMS.txt。旧 scripts/ 路径保留为兼容转发；历史Setup spec不用于当前发布。不同Python发行版的构建摘要可能不同。

使用短期分支和PR，最终提交的Linux与Windows CI通过后合并。发布时同步版本与CHANGELOG，从同一源码构建两个EXE；在已验证提交建立带注释标签，上传三个资产并核对摘要。预发布不替换稳定Latest；不移动已发布标签、不覆盖既有二进制资产。CI产物不会自动发布Release。

不得提交.env、真实运行日志、捕获资料、EXE或构建目录。实验源码在tools/experiments/，不进入正式安装包；原实验EXE继续独立保存。公开验证记录仅保留脱敏结果。

## 当前验证记录

81项正式测试、5项诊断测试、4项监测测试通过，1项依赖本地捕获资料的测试跳过。Linux核心与Windows完整CI通过；任务XML、载荷、实际冻结程序认证、特殊字符凭据和失败回滚已验证；本轮增加强制验证失败文字、维护二次状态变化、跨窗口边界、真实安装器跨进程锁和验收日志归属检查。

夜间验收应核对四项：任务按窗口启动、状态明确需认证时才登录、登录后查询确认恢复、窗口结束后退出。核对任务返回码及漏执行次数，详细日志保存在本地，不提交公开仓库。

仍待验收：持续维护模式长期运行与真实断网重连、睡眠/恢复、全新账户及完整安装向导。一次夜间成功不代表这些场景已经通过。程序不新增唤醒策略，夜间测试须保持电脑唤醒且连接UESTC。

历史版本演进索引见 [历史验证记录](history/VALIDATION-2026-10-06.md)。

## rc.5 WLAN优化候选

平台层改为WLAN API，频率、任务、电源与安装规则不变。新增资源对照与真实冻结WLAN检查；后者在CI没有已验证UESTC时明确跳过，本机已通过。实测和待完成的任务账户/睡眠/整夜验收见[资源优化](RESOURCE-OPTIMIZATION.md)。候选安装包仅构建验证，本轮未安装到本机；已发布候选仍为rc.4。

## rc.6审查与结构整理

修复文字成功前缀误判和未提交认证进入15秒冷却。文字成功改为完整格式匹配，重复否定规则合并；维护回调只接受LoginResult，删除整数兼容与重复类型分支，单次认证接口不变。81项单元回归覆盖新样例、在线强制验证、5秒重查和真正提交后15秒等待；冻结回归直接记录loopback服务收到POST的时间。

认证核心、通用循环、平台适配保持分层；旧入口适配层继续承担现有实验和旧接口兼容。rc.6 审阅发现安装器集中多种职责，已在 rc.7 整理。

资源性能表对应rc.5历史测量；rc.6/rc.7未重新跑完整开销比较。最新验收使用rc.7，见[发布验收](RELEASE-ACCEPTANCE.md)。

## rc.7 安装器整理

向导、文件部署事务、任务快照与恢复分开；备份、文件恢复和迁移清理各自集中。保留跨进程互斥、旧入口和完整回滚，不增加运行依赖。7种生成命令在Windows PowerShell中只做语法解析；真实临时任务恢复在管理员CI中验证。安装路径、两种模式、触发条件和电源策略保持原样；本轮不改本机安装状态。
