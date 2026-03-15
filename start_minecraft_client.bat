@echo off
REM Start Minecraft client with the mod

if not exist logs mkdir logs
set LOGFILE=%~dp0logs\minecraft_client.log

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting Minecraft client...
echo This may take a moment...
echo Logs: %LOGFILE%
echo.

echo [%date% %time%] ========== Minecraft client starting ========== >> "%LOGFILE%"

cd mod\minecraft-mod

echo Running Fabric dev client...
powershell -Command ".\gradlew.bat runClient 2>&1 | Tee-Object -Append -FilePath '%LOGFILE%'"

pause
