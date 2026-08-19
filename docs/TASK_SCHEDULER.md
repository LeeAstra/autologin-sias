# Windows Task Scheduler setup

Use `AutoLogin_SIAS_Headless.exe`, not the legacy browser automation EXE.

## Action

```text
Program/script:
D:\AutoLogin\AutoLogin_SIAS_Headless.exe

Start in:
D:\AutoLogin
```

Keep the `Start in` directory populated with `.env` and allow the program to write its log there.

## Security options

- `Run whether user is logged on or not` works for the headless build and may require the Windows account password.
- `Run only when user is logged on` also works while the workstation is locked.
- Do not use `cmd /k`, `cmd.exe`, a batch wrapper, or the old `pyautogui` build.

## Wi-Fi trigger

For a connection-triggered task, create an event trigger for:

```text
Log: Microsoft-Windows-WLAN-AutoConfig/Operational
Event ID: 8001
Delay: 30 seconds
```

SSID filtering can vary across Windows versions. If exact SSID filtering is unavailable, trigger on event 8001 and let the login program run its normal portal check.

## Conditions and settings

- Disable the condition requiring a specific network connection; the portal may not be authenticated yet when the task starts.
- Disable the AC-power-only condition if the task must work on battery.
- Stop the task after 2 minutes.
- If the task is already running, choose `Stop the existing instance`.

## Verification

Run the task manually once, then inspect `auto_login_headless.log`. A successful run includes:

```text
Background login request completed successfully
```
