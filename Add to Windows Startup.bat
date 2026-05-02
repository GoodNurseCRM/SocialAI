@echo off
:: Adds Good Nurse Agent to Windows startup so it runs automatically on login

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set AGENT_DIR=%~dp0
set BAT_FILE=%AGENT_DIR%Start Good Nurse Agent.bat

copy "%BAT_FILE%" "%STARTUP%\Good Nurse Agent.bat" >nul

echo Done! Good Nurse Agent will now start automatically every time you log in to Windows.
echo.
echo To remove it from startup, run "Remove from Windows Startup.bat"
pause
