# Development and release workflow

Develop on `codex/<feature>` branches, open a PR and require passing Windows CI before merging. The shared source version is in `src/app_version.py`: currently **1.2.0-rc.1**. Stable release **v1.1.0** remains unchanged until real-world acceptance passes. Update the changelog with each version; never move existing release tags.

Use Windows x64 and Python 3.13, preferably official CPython in a clean virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-TaskPreview.ps1
.\scripts\Build-Installer.ps1 -Python "$PWD\.venv\Scripts\python.exe"
.\.venv\Scripts\python.exe tests/check_bundle.py
```

CI runs the tests, builds the EXEs and retains artifacts with SHA-256 checksums. It never registers system tasks or publishes a Release automatically. Build dependencies are pinned; byte-identical builds across Python distributions are not guaranteed.

After manual acceptance, update the version/changelog, merge the reviewed PR, create a matching annotated tag and publish the installer with `SHA256SUMS.txt`. Mark RC releases as prereleases. See [VALIDATION.md](VALIDATION.md) for local results and size measurements.

## Release checklist

1. Run the credential audit:

   ```powershell
   rg -n -i "password|cookie|set-cookie|auth_tag=|pwd=|mac=|手机号|WLAN_USER=" .
   ```

2. Confirm only placeholders appear in tracked files.
3. Run `python src/auto_login_headless.py --version` and `--check`.
4. Build the Windows x64 EXEs with `packaging/auto_login_headless.spec` and `packaging/auto_login_headless_setup.spec`.
5. Put EXEs in a GitHub Release, not in the source repository.
6. Upload `.env.example` and `scripts/Install-AutoLoginTask.ps1` alongside the EXEs, never `.env`. Link `docs/TASK_SCHEDULER.md` in the release notes.
7. Test the downloaded EXE on a clean Windows account.
8. Build the single-file installer with `scripts/Build-Installer.ps1`; publish `packaging/dist/AutoLogin_SIAS_Installer.exe` as the recommended download. It embeds the freshly built headless EXE and task script.
9. Test installation, invalid credentials, denied UAC, reinstallation, existing task preservation, and Wi-Fi reconnection on Windows. Use the same administrator account throughout; cross-account elevation is unsupported. Confirm the installed files persist after deleting the downloaded installer.
