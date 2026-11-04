@echo off
cd /d "%~dp0"

if not exist "D:\Node.js\node.exe" goto PATH_NODE
"D:\Node.js\node.exe" launcher.js
goto CHECK_RESULT

:PATH_NODE
node.exe launcher.js

:CHECK_RESULT

if errorlevel 1 (
    echo.
    echo Project startup failed. Review the error message above.
    pause
    exit /b 1
)
