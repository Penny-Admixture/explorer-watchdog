# GOALS.md — Explorer Watchdog

## Done

- [x] **Build 1 (2026-11-23):** hang detection via SendMessageTimeout +
      SMTO_ABORTIFHUNG on Shell_TrayWnd; auto-restart (taskkill, wait for
      Winlogon auto-restart, manual fallback); 10-minute restart cooldown;
      PySide6 tray app with Check now / Restart now / Open log / Quit;
      clean-startup stale-instance kill; HKCU Run-key auto-start; unique
      icon (amber restart-arrow + eye) + AppUserModelID
      PennyAdmixture.ExplorerWatchdog; disk log + tray notifications;
      launch-hidden.vbs (style 0) + run.bat (no pause, log on failure).

## Awaiting Penny

- Live proof: run it, hang Explorer (or wait for a real hang), confirm
  the watchdog restarts it and the tray notification fires.

## Future

- Configurable check interval / cooldown (a small settings file).
- Optional: restart only after N consecutive failed pings (currently 1).
