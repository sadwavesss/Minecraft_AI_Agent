@echo off
REM Start Minecraft client with the mod

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting Minecraft client...
echo This may take a moment...
echo.

cd mod\minecraft-mod

echo Running Fabric dev client...
call gradlew.bat runClient

pause
