# 维护与验证

面向维护者；首次安装、迁移目录和 VPN 排障请看 [使用指南](USAGE.md)。

## 构建与发布

Current public version: **v1.2.0**, marked **Latest** on GitHub. `src/app_version.py` is the single version source for the background program and installer. RC releases and v1.1.0 remain historical releases; do not mix their assets with the current release.

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
