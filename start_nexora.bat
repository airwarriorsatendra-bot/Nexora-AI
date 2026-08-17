@echo off
setlocal

cd /d "%~dp0"

echo Starting Nexora AI...
echo.
echo Dashboard: http://localhost:8501
echo.

start "" "http://localhost:8501"

".venv\Scripts\python.exe" -m streamlit run dashboard\app.py --server.port 8501

if errorlevel 1 (
    echo.
    echo Nexora AI failed to start.
    pause
)

endlocal