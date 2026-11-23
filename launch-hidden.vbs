' Launch Explorer Watchdog with NO console window at all.
' Penny 2026-11-19: background always -- the app itself runs under pyw
' (windowless), but the .bat chain owns a cmd console at every launch.
' Point the double-click / Startup entry at this .vbs instead of run.bat
' and the console never appears. The tray icon is the only visible part.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\run.bat"
sh.Run """" & batPath & """", 0, False
