@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
	echo Virtual-environment Python interpreter not found.
	exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
endlocal
