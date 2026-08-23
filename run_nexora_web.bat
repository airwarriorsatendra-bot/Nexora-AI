@echo off
setlocal
cd /d "%~dp0"
start "Nexora API" /b cmd /c run_api.bat
start "Nexora Web" /b cmd /c run_web.bat
echo Nexora API and web development servers started.
endlocal
