@echo off
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
del "%STARTUP%\Good Nurse Agent.bat" >nul 2>&1
echo Removed Good Nurse Agent from Windows startup.
pause
