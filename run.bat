@echo off
REM Explorer Watchdog launcher. git pull, then double-click launch-hidden.vbs
REM (or `run` from a terminal here).
REM Penny 2026-11-23: background always -- the app runs under pyw (the
REM windowed launcher, no console at all). Double-click launch-hidden.vbs
REM instead of this file: style 0, no console at all.
REM The app registers itself in the HKCU Run key on first launch, so it
REM starts at every login after that -- set and forget.
cd /d %~dp0
pyw explorer_watchdog.py %*
if errorlevel 1 (
  echo [%date% %time%] Explorer Watchdog failed to launch (error code %errorlevel%). >> launch-errors.log
  exit /b 1
)
