# Release checklist

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
