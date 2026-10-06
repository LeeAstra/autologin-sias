# 维护与验证

面向维护者；首次安装、迁移目录和 VPN 排障请看 [使用指南](USAGE.md)。

## 构建与发布

### 2026-10-05 工作区候选：先检测再登录

基于独立实验的既有接口证据调整正式程序的单次执行流程；未改安装器、任务脚本、触发时间或电源条件。原有本地循环实验及其 EXE 保留，继续使用原监测 EXE 保持夜间实验版本一致。供公开维护的源码整理到 `tools/experiments/`，独立目录和 CI 另行验证。

验证：22 项源码单元/本机 HTTP 集成测试通过；新构建 `packaging/dist/AutoLogin_SIAS_Headless.exe` 的本机代理回归通过，覆盖已认证跳过、未知状态继续认证、响应成功但后状态未确认返回 8、原失败退出码、特殊字符密码，以及使用真实子 EXE 的模拟安装成功和失败回滚。测试使用合成凭据，不访问真实门户、不注册 Windows 任务。新版尚未进行真实校园网验证，也未替换已安装 EXE。

构建环境：本机 Anaconda Python 3.13.5 / PyInstaller 6.17.0。该阶段仅构建后台候选，未更新公开 v1.2.0 资产。v1.3.0-rc.1 安装器与后台程序需重新从同一提交构建，校验值以该 Release 的 SHA256SUMS.txt 为准。

Current public version: **v1.2.0**, marked **Latest** on GitHub. `src/sias_autologin/version.py` is the single version source for the background program and installer. RC releases and v1.1.0 remain historical releases; do not mix their assets with the current release.

### Build and validate

Use Windows x64 and Python 3.13, preferably official CPython in a clean virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-TaskPreview.ps1
.\scripts\Build-Installer.ps1 -Python "$PWD\.venv\Scripts\python.exe"
.\.venv\Scripts\python.exe tests/check_bundle.py
.\.venv\Scripts\python.exe tests/check_frozen_login.py
```

Current release assets, all from the same build:

- `packaging/dist/AutoLogin_SIAS_Installer.exe`: recommended single-file deployment.
- `packaging/dist/AutoLogin_SIAS_Headless.exe`: standalone background program for existing/custom installations.
- `packaging/dist/SHA256SUMS.txt`: SHA-256 manifest for both EXEs.

The old Setup EXE is not part of the current release. Its spec is retained only for historical compatibility. Build dependencies are pinned, but different Python distributions can produce different binary hashes.

### Publish

1. Develop on a feature/release branch. Update the shared version, changelog and current-version links together.
2. Review tracked changes for credentials, real logs and generated files. These must not be committed.
3. Run the tests and build both EXEs. Verify frozen CLI commands, embedded payloads and checksums. Record evidence and untested scenarios in [验证记录](#验证记录).
4. Open a PR and wait for Windows CI on the final submitted commit before merging.
5. Create a matching annotated tag on the merged commit; never move a published tag.
6. Publish the three assets above and user-facing release notes. For a public release, explicitly mark it **Latest**. RC tags remain prereleases and do not replace the Latest download entry.
7. Verify the public `releases/latest` endpoint points to the intended tag, and asset digests match the local binaries.
8. Keep prior releases for rollback/history; add a link to the current release in their notes rather than deleting or replacing old artifacts.

CI creates build artifacts but does not publish Releases automatically. Publishing does not imply that untested scenarios have passed: the current validation report explicitly retains the full wizard/UAC, clean-account, lock-screen and reconnect limitations.

## 验证记录

### 2026-10-06 维护模式候选 rc.2

37项正式测试通过，包括通用循环、时间窗口、SSID许可复查、安装向导目录/模式、迁移清理边界及Windows原生文件替换兼容；诊断5项、监测4项通过，捕获资料测试1项跳过。任务XML验证两种新模式、旧模式兼容、电源保留和Exec元素顺序。两个EXE构建、载荷/依赖检查、冻结维护窗口外退出及实际EXE认证/凭据保真/回滚通过。

本机升级发现默认安装目录启用文件加密：同目录os.replace返回WinError17，Windows允许复制的MoveFileEx可完成；已限定暂存目录并增加回归，实目录合成文件验证通过。实际升级随后在凭据验证阶段遇到门户连接失败，已回滚并恢复旧任务。只读路由检查显示2.2.2.3走Meta虚拟网卡；暂未改网络路由。不能将本次尝试视为新版任务实机验收。

待验收：当前网络恢复后的安装/真实认证，夜间窗口执行、持续模式断网重连、睡眠恢复，以及完整新安装向导/UAC。稳定Latest保持v1.2.0。


### 2026-10-05 分层重构

认证核心、CLI/配置和 Windows 适配分离，详见 [代码结构](ARCHITECTURE.md)。旧源码入口和命令脚本继续兼容；正式任务脚本迁移前后逐行一致。源码版本仍为 1.3.0-rc.1，本次源码修改尚未发布新的 Release 资产。

本机通过 29 项正式测试、5 项诊断测试和4 项监测测试；1 项依赖本地抓包资料的测试跳过。两个 EXE 构建成功，安装包载荷/版本检查与实际 EXE 本机模拟认证和安装回滚回归通过。使用合成凭据，不注册系统任务。新增 Linux 核心 CI 验证导入边界、直接 API 和旧接口。


### v1.2.0 release scope

v1.2.0 promotes the rc.2 implementation to the current public release and reorganizes the documentation. The only runtime-source change from rc.2 is the shared version identifier; authentication, installation and task logic are unchanged. EXEs are rebuilt with the final version and receive new checksums. The checks below are retained as historical evidence; this release does not claim full wizard/UAC, clean-account, lock-screen or reconnect acceptance.

On 2026-09-24, the v1.2.0 rebuild passed all 18 Python tests, task XML tests, frozen payload/CLI checks and actual EXE response/credential/rollback regression checks. The local installer is 16,317,941 bytes. The published SHA256SUMS.txt identifies this build; do not use a checksum from an RC release.

### 1.2.0-rc.2 review follow-up

The password-whitespace review finding was confirmed and fixed. Installer and setup now share a versioned, lossless credential writer/reader; RC4 no longer strips the password. Legacy `.env` files retain their original parsing rules. New-format configuration requires rc.2 or later; restore the old configuration when rolling back to an older binary.

18 Python tests and task XML preview checks pass. Frozen regression checks additionally verify that whitespace, quotes and backslashes reach the encryption step unchanged. A transient Windows file-lock failure during reinstallation was reproduced and fixed with staged replacement, bounded retries and rollback limited to changed files; regression checks then passed.

The rebuilt installer is 16,319,693 bytes. Its embedded payload and frozen CLI checks pass. The rc.2 background EXE was deployed after a local backup and executed through the existing scheduled task on 2026-09-23 at 17:20: authentication succeeded and the task returned 0. Task XML and the credential-file hash were unchanged; the next run remained 04:10. This does not verify fresh task registration or the interactive UAC flow.

The review's spec-name finding does not match the checked-in files: `auto_login_headless.spec` emits `AutoLogin_SIAS_Headless`, while `auto_login_headless_setup.spec` emits `AutoLogin_SIAS_Setup`. Both clean Windows CI runs for rc.1's final commit `bd209d3` passed; the scripts were not swapped.

### Historical 1.2.0-rc.1 results

Local validation date: 2026-09-23. Windows x64, Conda Python 3.13.5, PyInstaller 6.17.0, hooks 2025.11.

### Verified locally

- 12 Python tests: install success/failure, rollback on login failure or cancellation, task-registration failure retention, credential argument isolation, malformed input, RC4 known vector, response parsing, configuration loading, missing credentials and network timeout.
- A local HTTP server integration test exercises actual urllib requests, cookies and form encoding with synthetic credentials.
- Windows PowerShell 5.1 XML tests verify new event/daily settings, existing schedule/power preservation, missing working-directory repair and rejection of a daily override on existing tasks. They never register system tasks.
- Both EXEs build. The installer archive contains byte-identical copies of the current background EXE and PowerShell script.
- Frozen installer `--version` / `--verify-payload` and background EXE `--version` exit successfully. These checks suppress UAC only for read-only diagnostics and do not run the deployment wizard.
- The build produces SHA-256 checksums alongside the EXEs.
- Frozen EXE loopback-proxy regression tests pass for successful authentication, explicit rejection, boolean rejection, unknown HTML, empty responses and HTTP 503. The deployment function also runs the real child EXE and verifies successful deployment plus rollback after failed authentication; only task registration is substituted in this test.
- On 2026-09-23, the candidate background EXE was manually run with `--check` on an existing UESTC connection using the existing local configuration. Portal and jump requests returned HTTP 200, the response was recognized as successful, and the process exited 0. A subsequent external HTTPS HEAD request returned 200. This verifies a real request on an already-connected machine, not recovery from disconnection.
- Read-only inspection found the existing task ready, its last result 0 and its next run scheduled for 04:10. This task was not modified or triggered by the regression tests and does not establish candidate task execution.
- After explicit upgrade authorization, the existing task executable was backed up and replaced with the verified candidate on 2026-09-23. Running the actual scheduled task at 16:25 completed with result 0 and successful portal/jump logs. The task XML was byte-for-byte unchanged; its next daily run remained 04:10. The old EXE and task XML were retained locally for recovery; credentials were unchanged.

### Size comparison

| Local build | Bytes | Decimal MB |
|---|---:|---:|
| Initial one-file installer | 18,661,089 | 18.66 |
| Candidate installer | 16,315,460 | 16.32 |

The candidate is 2,345,629 bytes (12.6%) smaller. The installer does not need `_hashlib`; excluding that optional extension removes its otherwise unnecessary OpenSSL crypto DLL. The embedded background EXE keeps its TLS dependencies. No additional runtime dependencies were introduced.

The remaining large components are the embedded headless EXE and the installer's own Python runtime. A native installer could avoid the second runtime, but would add a new toolchain and require separate deployment/upgrade testing. This candidate retains the existing Python deployment implementation. Size depends on build environment and is not a universal guarantee.

PyInstaller supports configuring analysis through [spec files](https://pyinstaller.org/en/stable/spec-files.html); CI follows the [GitHub Python workflow guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

### Not yet verified

UAC interaction, the full frozen installer wizard, actual task registration under the intended account, reconnect/lock-screen/daily execution and clean-machine installation remain manual acceptance items. Automated regression tests use only synthetic credentials; the separate real-network check reused local credentials without printing or modifying them. The rc.1 report treated the build as a candidate pending those checks; later verification and release decisions are recorded above.

An unknown portal response now exits with code 8 instead of reporting success. If the actual portal uses a currently unsupported success response, capture a sanitized response structure and extend the parser with a regression test before release.

## 提交前安全检查

- `.env` 必须在忽略列表中，并确认没有被 Git 跟踪。
- 只允许提交示例占位符和测试用虚构凭据。
- 不提交构建目录、EXE、虚拟环境或运行日志；发布 EXE 使用 GitHub Release。
- 检查文档、截图和历史提交中是否包含真实凭据。若已公开泄露，应更换对应凭据。
