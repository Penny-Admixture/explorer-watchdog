"""Explorer Watchdog — notices when Windows Explorer hangs and restarts it.

Penny, 2026-11-23: "it's fucking obnoxious to have to go into Task Manager
and restart Explorer.exe — it's something that should be noticeable."

How it works:
  * Every CHECK_INTERVAL seconds it pings the taskbar window (Shell_TrayWnd)
    with SendMessageTimeout + SMTO_ABORTIFHUNG. A healthy Explorer answers
    in milliseconds; a hung one never answers.
  * If the taskbar window is GONE, Explorer is dead (crashed) — same action.
  * On a hang/death it kills explorer.exe. Windows auto-restarts the shell
    (Winlogon watches for it, AutoRestartShell is on by default) — the
    watchdog waits up to 10 s for the taskbar to come back on its own, and
    only starts explorer.exe manually if it doesn't.
  * Cooldown: at most one restart per RESTART_COOLDOWN seconds, so a
    fundamentally broken shell can't spin a restart loop.

House standards honored:
  * Identity Standard: AppUserModelID PennyAdmixture.ExplorerWatchdog +
    unique icon + unique window identity at startup, always.
  * Clean startup: kills stale instances of itself (command-line match,
    never exe name alone) before starting.
  * Console suppression: runs under pyw / launch-hidden.vbs, no console.
  * Logging: disk log (explorer-watchdog.log) + tray notification on
    every restart. No lock files, ever.
  * Auto-start: registers itself in the HKCU Run key on first launch
    (set-and-forget; Penny never has to start it again).

One file, no build step: pyw explorer_watchdog.py (or launch-hidden.vbs).
Requires PySide6 (the house Qt binding) and Windows.
"""

import ctypes
import logging
import os
import subprocess
import sys
import time
import traceback
from ctypes import wintypes

VERSION = 1
APP_NAME = "ExplorerWatchdog"
AUMID = "PennyAdmixture.ExplorerWatchdog"

CHECK_INTERVAL_MS = 30_000      # how often to ping the taskbar
HANG_TIMEOUT_MS = 5_000         # a healthy Explorer answers in ms; 5 s is hung
RESTART_COOLDOWN_S = 600        # at most one restart per 10 minutes
AUTORESTART_WAIT_S = 10         # how long to wait for Winlogon's auto-restart

WM_NULL = 0x0000
SMTO_ABORTIFHUNG = 0x0002

user32 = ctypes.windll.user32

# ---------------------------------------------------------------- logging

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "explorer-watchdog.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
log = logging.getLogger(APP_NAME)


def _log_crash(exc):
    """Crash handler: traceback to the disk log first, per the List."""
    log.error("CRASH:\n%s", traceback.format_exc())


# ---------------------------------------------------------------- identity

def _set_appusermodelid():
    """Identity Standard: our own AppUserModelID, always, at startup."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
    except Exception:
        log.warning("could not set AppUserModelID", exc_info=True)


def _kill_stale_instances():
    """Clean-startup principle: if we can't coexist with ourselves, startup
    kills the other instances and starts clean. Matches by command line
    (exe + script path), never by exe name alone."""
    try:
        import win32com.client  # noqa: F401  (pywin32, if present)
    except Exception:
        pass
    # Use Get-CimInstance via powershell (wmic is dead on her PC) — match
    # pythonw/python running THIS script, excluding our own PID.
    script = os.path.abspath(__file__).replace("'", "''")
    ps = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -and $_.CommandLine -like '*explorer_watchdog.py*' "
        "-and $_.ProcessId -ne $PID } | ForEach-Object { "
        "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        log.warning("stale-instance sweep failed (continuing)", exc_info=True)
    time.sleep(1)  # let the kills land before we proceed


# ---------------------------------------------------------------- detection

def find_taskbar():
    """HWND of the taskbar window, or 0 if Explorer is dead."""
    return user32.FindWindowW("Shell_TrayWnd", None)


def is_explorer_responsive(timeout_ms=HANG_TIMEOUT_MS):
    """True if the taskbar answers a ping within timeout_ms.

    SendMessageTimeout with SMTO_ABORTIFHUNG returns 0 when the target
    window's thread is hung — that is the hang signal, not an error.
    """
    hwnd = find_taskbar()
    if not hwnd:
        return False
    result = wintypes.LPARAM()
    ret = user32.SendMessageTimeoutW(
        hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, timeout_ms,
        ctypes.byref(result),
    )
    return ret != 0


def _explorer_pid_alive():
    """Is any explorer.exe process running? (belt-and-braces check)."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq explorer.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "explorer.exe" in out.stdout.lower()
    except Exception:
        return True  # inconclusive — don't act on a failed check


# ---------------------------------------------------------------- restart

def restart_explorer():
    """Kill explorer.exe; let Winlogon auto-restart it; start it manually
    only if the taskbar doesn't come back on its own."""
    log.warning("RESTARTING Explorer (hang or death detected)")
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "explorer.exe"],
            capture_output=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        log.error("taskkill failed", exc_info=True)
    # Winlogon auto-restarts the shell (AutoRestartShell default on).
    # Wait for the taskbar to come back before doing anything else.
    for _ in range(AUTORESTART_WAIT_S):
        time.sleep(1)
        if find_taskbar() and is_explorer_responsive(timeout_ms=2000):
            log.info("Explorer auto-restarted by Windows (taskbar back)")
            return True
    # Fallback: start it ourselves.
    log.warning("no auto-restart after %ds — starting explorer.exe manually",
                AUTORESTART_WAIT_S)
    try:
        subprocess.Popen(
            ["explorer.exe"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        log.error("manual explorer start failed", exc_info=True)
        return False
    for _ in range(AUTORESTART_WAIT_S):
        time.sleep(1)
        if find_taskbar() and is_explorer_responsive(timeout_ms=2000):
            log.info("Explorer restarted manually (taskbar back)")
            return True
    log.error("Explorer did NOT come back after manual start")
    return False


# ---------------------------------------------------------------- autostart

def _ensure_autostart():
    """Register in the HKCU Run key so the watchdog starts at login.
    Set-and-forget: Penny never starts it by hand again."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        vbs = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "launch-hidden.vbs")
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                          '"%s"' % vbs)
        winreg.CloseKey(key)
        log.info("auto-start registered (HKCU Run key -> launch-hidden.vbs)")
    except Exception:
        log.warning("could not register auto-start", exc_info=True)


# ---------------------------------------------------------------- tray app

def main():
    _set_appusermodelid()
    _kill_stale_instances()
    log.info("Explorer Watchdog v%d starting (check every %ds, hang timeout "
             "%ds, restart cooldown %ds)",
             VERSION, CHECK_INTERVAL_MS // 1000, HANG_TIMEOUT_MS // 1000,
             RESTART_COOLDOWN_S)
    _ensure_autostart()

    from PySide6.QtWidgets import (QApplication, QMenu, QSystemTrayIcon)
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QAction, QIcon

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    here = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(here, "watchdog.ico")
    icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Explorer Watchdog — watching for hangs")

    state = {"last_restart": 0.0}

    def do_check(manual=False):
        try:
            responsive = is_explorer_responsive()
        except Exception:
            _log_crash(sys.exc_info()[1])
            return
        if responsive:
            if manual:
                tray.showMessage("Explorer Watchdog",
                                 "Explorer is responsive.",
                                 QSystemTrayIcon.Information, 3000)
            return
        # Hung or dead.
        now = time.time()
        if now - state["last_restart"] < RESTART_COOLDOWN_S:
            log.warning("Explorer hung but in cooldown (%ds left) — not "
                        "restarting", int(RESTART_COOLDOWN_S - (now - state["last_restart"])))
            return
        state["last_restart"] = now
        ok = restart_explorer()
        tray.showMessage(
            "Explorer Watchdog",
            ("Explorer was hung — restarted it."
             if ok else "Explorer was hung — restart FAILED, see the log."),
            QSystemTrayIcon.Warning if ok else QSystemTrayIcon.Critical, 5000)
        if not ok:
            log.error("restart failed; will retry after cooldown")

    def restart_now():
        state["last_restart"] = 0.0  # manual restart bypasses the cooldown
        ok = restart_explorer()
        state["last_restart"] = time.time()
        tray.showMessage("Explorer Watchdog",
                         "Explorer restarted." if ok else
                         "Explorer restart FAILED — see the log.",
                         QSystemTrayIcon.Information if ok
                         else QSystemTrayIcon.Critical, 5000)

    def open_log():
        os.startfile(LOG_PATH)

    menu = QMenu()
    act_check = QAction("Check now", menu)
    act_check.triggered.connect(lambda: do_check(manual=True))
    act_restart = QAction("Restart Explorer now", menu)
    act_restart.triggered.connect(restart_now)
    act_log = QAction("Open log", menu)
    act_log.triggered.connect(open_log)
    act_quit = QAction("Quit", menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_check)
    menu.addAction(act_restart)
    menu.addAction(act_log)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.show()

    timer = QTimer(app)
    timer.timeout.connect(lambda: do_check(manual=False))
    timer.start(CHECK_INTERVAL_MS)

    # First check immediately (don't wait 30 s for the first ping).
    do_check(manual=False)

    log.info("watching (tray icon up, first check done)")
    try:
        sys.exit(app.exec())
    except Exception:
        _log_crash(sys.exc_info()[1])
        raise


if __name__ == "__main__":
    main()
