# 维护与验证

当前源码与最新预发布为 **v1.3.0-rc.3**；稳定 Latest 仍为 **v1.2.0**。唯一版本来源是 `src/sias_autologin/version.py`。不同版本安装器和后台EXE不得混用。

代码组织见 [三层架构](ARCHITECTURE.md)，安装与模式选择见 [rc.3指南](releases/v1.3.0-rc.3.md)，全部入口见 [文档索引](README.md)。

## 构建与发布

使用 Windows x64 / Python 3.13，安装 `requirements-build.txt` 后运行：

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tools/experiments/login-diagnostics -v
python -m unittest discover -s tools/experiments/login-monitor -v
powershell -NoProfile -ExecutionPolicy Bypass -File tests/Test-TaskPreview.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build/Build-Installer.ps1
python tests/check_task_recovery.py
python tests/check_bundle.py
python tests/check_frozen_login.py
```

产物位于 `packaging/dist/`：安装器EXE、后台EXE及SHA256SUMS.txt。旧 scripts/ 路径保留为兼容转发；历史Setup spec不用于当前发布。不同Python发行版的构建摘要可能不同。

使用短期分支和PR，最终提交的Linux与Windows CI通过后合并。发布时同步版本与CHANGELOG，从同一源码构建两个EXE；在已验证提交建立带注释标签，上传三个资产并核对摘要。预发布不替换稳定Latest；不移动已发布标签、不覆盖既有二进制资产。CI产物不会自动发布Release。

不得提交.env、真实运行日志、捕获资料、EXE或构建目录。实验源码在tools/experiments/，不进入正式安装包；原实验EXE继续独立保存。公开验证记录仅保留脱敏结果。

## 当前验证记录

44项正式测试、5项诊断测试、4项监测测试通过，1项依赖本地捕获资料的测试跳过。Linux核心与Windows完整CI通过；任务XML、载荷、实际冻结程序认证、特殊字符凭据和失败回滚已验证。

夜间验收应核对四项：任务按窗口启动、状态明确需认证时才登录、登录后查询确认恢复、窗口结束后退出。核对任务返回码及漏执行次数，详细日志保存在本地，不提交公开仓库。

仍待验收：持续维护模式长期运行与真实断网重连、睡眠/恢复、全新账户及完整安装向导。一次夜间成功不代表这些场景已经通过。程序不新增唤醒策略，夜间测试须保持电脑唤醒且连接UESTC。

历史版本演进索引见 [历史验证记录](history/VALIDATION-2026-10-06.md)。
