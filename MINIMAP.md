# MINIMAP.md — Explorer Watchdog

One-file PySide6 tray app that watches Windows Explorer and restarts it
when it hangs or dies.

## Layout

```
explorer-watchdog/
  explorer_watchdog.py   the whole app
  watchdog.ico           unique tray/taskbar icon (256..16 px)
  watchdog.png           icon source
  run.bat                pyw launcher (log-on-failure, no pause)
  launch-hidden.vbs      style-0 hidden launcher (double-click this)
  README.md  GOALS.md  MINIMAP.md
  explorer-watchdog.log  runtime log (created on first run)
```

## How it works

- **Detection:** `is_explorer_responsive()` — `FindWindowW("Shell_TrayWnd")`
  then `SendMessageTimeoutW(hwnd, WM_NULL, SMTO_ABORTIFHUNG, 5000)`.
  Returns False if the taskbar is gone (dead) or doesn't answer (hung).
- **Restart:** `restart_explorer()` — `taskkill /F /IM explorer.exe`,
  wait up to 10 s for Winlogon's auto-restart (taskbar back + responsive),
  else `Popen(["explorer.exe"])` and wait again.
- **Cooldown:** `RESTART_COOLDOWN_S = 600` — at most one restart per
  10 min (manual "Restart now" bypasses it).
- **Loop:** QTimer every `CHECK_INTERVAL_MS = 30000`, plus an immediate
  first check at startup.
- **Identity:** `SetCurrentProcessExplicitAppUserModelID(
  "PennyAdmixture.ExplorerWatchdog")` at startup, always.
- **Clean startup:** `_kill_stale_instances()` — Get-CimInstance match on
  `*explorer_watchdog.py*` in the command line, excluding own PID.
- **Auto-start:** `_ensure_autostart()` — HKCU Run key ->
  launch-hidden.vbs, on first launch.
- **Logging:** `explorer-watchdog.log` (disk); crash handler writes the
  traceback to the log first. Tray notification on every restart.

## Gotchas

- `wmic` is dead on her PC (Win 11 26H2) — Get-CimInstance only.
- Killing explorer.exe closes open Explorer windows (unavoidable; a hung
  Explorer's windows were unusable anyway).
- Windows auto-restarts the shell after a kill (AutoRestartShell default
  on) — the manual `Popen` is only a fallback.
