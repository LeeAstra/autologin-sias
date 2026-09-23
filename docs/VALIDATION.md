# 1.2.0-rc.1 validation and package size

Local validation date: 2026-09-23. Windows x64, Conda Python 3.13.5, PyInstaller 6.17.0, hooks 2025.11.

## Verified locally

- 12 Python tests: install success/failure, rollback on login failure or cancellation, task-registration failure retention, credential argument isolation, malformed input, RC4 known vector, response parsing, configuration loading, missing credentials and network timeout.
- A local HTTP server integration test exercises actual urllib requests, cookies and form encoding with synthetic credentials.
- Windows PowerShell 5.1 XML tests verify new event/daily settings, existing schedule/power preservation, missing working-directory repair and rejection of a daily override on existing tasks. They never register system tasks.
- Both EXEs build. The installer archive contains byte-identical copies of the current background EXE and PowerShell script.
- Frozen installer `--version` / `--verify-payload` and background EXE `--version` exit successfully. These checks suppress UAC only for read-only diagnostics and do not run the deployment wizard.
- The build produces SHA-256 checksums alongside the EXEs.
- Frozen EXE loopback-proxy regression tests pass for successful authentication, explicit rejection, boolean rejection, unknown HTML, empty responses and HTTP 503. The deployment function also runs the real child EXE and verifies successful deployment plus rollback after failed authentication; only task registration is substituted in this test.
- On 2026-09-23, the candidate background EXE was manually run with `--check` on an existing UESTC connection using the existing local configuration. Portal and jump requests returned HTTP 200, the response was recognized as successful, and the process exited 0. A subsequent external HTTPS HEAD request returned 200. This verifies a real request on an already-connected machine, not recovery from disconnection.
- Read-only inspection found the existing task ready, its last result 0 and its next run scheduled for 04:10. This task was not modified or triggered by the regression tests and does not establish candidate task execution.

## Size comparison

| Local build | Bytes | Decimal MB |
|---|---:|---:|
| Initial one-file installer | 18,661,089 | 18.66 |
| Candidate installer | 16,315,460 | 16.32 |

The candidate is 2,345,629 bytes (12.6%) smaller. The installer does not need `_hashlib`; excluding that optional extension removes its otherwise unnecessary OpenSSL crypto DLL. The embedded background EXE keeps its TLS dependencies. No additional runtime dependencies were introduced.

The remaining large components are the embedded headless EXE and the installer's own Python runtime. A native installer could avoid the second runtime, but would add a new toolchain and require separate deployment/upgrade testing. This candidate retains the existing Python deployment implementation. Size depends on build environment and is not a universal guarantee.

PyInstaller supports configuring analysis through [spec files](https://pyinstaller.org/en/stable/spec-files.html); CI follows the [GitHub Python workflow guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## Not yet verified

UAC interaction, the full frozen installer wizard, actual task registration under the intended account, reconnect/lock-screen/daily execution and clean-machine installation remain manual acceptance items. Automated regression tests use only synthetic credentials; the separate real-network check reused local credentials without printing or modifying them. Keep this version a candidate until those checks pass.

An unknown portal response now exits with code 8 instead of reporting success. If the actual portal uses a currently unsupported success response, capture a sanitized response structure and extend the parser with a regression test before release.
