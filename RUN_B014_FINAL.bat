@echo off
cd /d "%~dp0"
echo.
echo BYTE NDT - B014 TRUE TWIN - LIVING ENGINEERING
echo 2D MATRIX 8x8 - 55 DEG SW - SECTORIAL 35 TO 70 - SKEW MINUS 10 TO PLUS 10
echo.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8507" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
start "" http://localhost:8507
python -m streamlit run "B014_TRUE_TWIN_LIVING_ENGINEERING_FINAL.py" --server.port 8507
pause
