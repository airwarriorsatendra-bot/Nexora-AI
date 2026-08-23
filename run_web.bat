@echo off
setlocal
cd /d "%~dp0web"
set "PATH=C:\Program Files\nodejs;%PATH%"
call npm.cmd run dev
endlocal
