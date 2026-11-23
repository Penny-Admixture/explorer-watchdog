# Explorer Watchdog

Notices when Windows Explorer hangs and restarts it — so Penny never has
to go into Task Manager and restart `explorer.exe` by hand again.

## How it works

Every 30 seconds it pings the taskbar window (`Shell_TrayWnd`) with
`SendMessageTimeout` + `SMTO_ABORTIFHUNG`. A healthy Explorer answers in
milliseconds; a hung one never answers. If the taskbar window is gone
entirely, Explorer is dead (crashed) — same action.

On a hang or death it kills `explorer.exe`. Windows auto-restarts the
shell on its own (Winlogon watches for it); the watchdog waits up to 10
seconds for the taskbar to come back, and only starts `explorer.exe`
manually if it doesn't. A tray notification says what happened, and
every restart is logged to `explorer-watchdog.log`.

Cooldown: at most one restart per 10 minutes, so a fundamentally broken
shell can't spin a restart loop.

## Run it

```
git pull
```
then double-click `launch-hidden.vbs`. No console window, ever. The app
registers itself in the HKCU Run key on first launch, so it starts at
every login after that — set and forget.

Tray menu: Check now / Restart Explorer now / Open log / Quit.

## House standards

- **Identity Standard:** AppUserModelID `PennyAdmixture.ExplorerWatchdog`,
  unique icon (amber restart-arrow + eye), own taskbar/tray item.
- **Clean startup:** kills stale instances of itself (command-line match)
  before starting.
- **Console suppression:** pyw + launch-hidden.vbs (style 0), no console.
- **Logging:** disk log + tray notification on every restart. No lock files.
- **Auto-start:** HKCU Run key, registered on first launch.

## Files

- `explorer_watchdog.py` — the whole app (one file, PySide6 tray + win32)
- `watchdog.ico` / `watchdog.png` — unique icon
- `run.bat` — pyw launcher (failures go to `launch-errors.log`, no pause)
- `launch-hidden.vbs` — style-0 hidden launcher
- `explorer-watchdog.log` — created at runtime
