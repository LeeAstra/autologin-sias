# Build and release workflow

Current public version: **v1.2.0**, marked **Latest** on GitHub. `src/app_version.py` is the single version source for the background program and installer. RC releases and v1.1.0 remain historical releases; do not mix their assets with the current release.

## Build and validate

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

## Publish

1. Develop on a feature/release branch. Update the shared version, changelog and current-version links together.
2. Review tracked changes for credentials, real logs and generated files. These must not be committed.
3. Run the tests and build both EXEs. Verify frozen CLI commands, embedded payloads and checksums. Record evidence and untested scenarios in [VALIDATION.md](VALIDATION.md).
4. Open a PR and wait for Windows CI on the final submitted commit before merging.
5. Create a matching annotated tag on the merged commit; never move a published tag.
6. Publish the three assets above and user-facing release notes. For a public release, explicitly mark it **Latest**. RC tags remain prereleases and do not replace the Latest download entry.
7. Verify the public `releases/latest` endpoint points to the intended tag, and asset digests match the local binaries.
8. Keep prior releases for rollback/history; add a link to the current release in their notes rather than deleting or replacing old artifacts.

CI creates build artifacts but does not publish Releases automatically. Publishing does not imply that untested scenarios have passed: the current validation report explicitly retains the full wizard/UAC, clean-account, lock-screen and reconnect limitations.
