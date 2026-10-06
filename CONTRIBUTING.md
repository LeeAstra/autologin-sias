# 参与和维护

本项目采用 GitHub Flow：`main` 保存已完成检查的代码，改动使用短期分支和 Pull Request。建议分支名 `codex/简短主题`，每个 PR 集中处理一项可独立说明的改动。合并后删除远端功能分支；PR、提交历史和版本标签仍保留。

## 修改与验证

分层设计与跨平台开发入口见 [代码结构](docs/ARCHITECTURE.md)。认证核心在 `src/sias_autologin/core/`，可跨平台循环在 `runtime/`，Windows 适配在 `platforms/windows/`。正式认证程序在 `src/`，安装与任务脚本在 `scripts/`，实验工具在 `tools/experiments/`。实验代码不纳入安装包。改动任务条件或认证协议时，必须在 PR 中明确说明；普通状态检测调整不应顺带改变触发时间或电源设置。

安装构建依赖后，在 Windows / Python 3.13 运行：

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tools/experiments/login-diagnostics -v
python -m unittest discover -s tools/experiments/login-monitor -v
powershell -ExecutionPolicy Bypass -File .\tests\Test-TaskPreview.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Build-Installer.ps1
python tests/check_bundle.py
python tests/check_frozen_login.py
```

自动测试使用合成凭据和本机门户，不应触发真实认证或注册系统任务。真实校园网、UAC、锁屏和连接事件验证另行记录，不能用 CI 成功代替实机验证。

## 版本与发布

`src/sias_autologin/version.py` 为唯一版本来源。新增向后兼容功能递增次版本，修复递增补丁版本；未完成必要实机验证时使用 `-rc.N` 预发布。同步维护 `CHANGELOG.md`、说明和 Release，标签为 `v版本号`，指向实际验证过的提交。

合并前 CI 必须通过。安装器和后台 EXE 从同一提交构建并验证，发布二者及 `SHA256SUMS.txt`；EXE 放在 Release Assets，不能提交到源码仓库。预发布不得覆盖稳定版或设为 Latest。发布后校验标签、源码版本、资产校验和一致，再更新本地 `main`。不重新移动已经发布的标签。

不要提交 `.env`、密码、Cookie、真实资料、抓包或实验结果。报告问题使用合成样例、程序版本和脱敏错误；不要把凭据粘贴到公开 Issue。
