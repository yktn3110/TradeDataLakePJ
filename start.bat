@echo off
echo Starting TradeDataLakePJ...
docker compose up -d
if %ERRORLEVEL% neq 0 (
    echo Failed to start. Is Docker Desktop running?
    pause
    exit /b 1
)
echo.
echo Started successfully.
echo   Grafana : http://localhost:3000  (admin / admin)
echo   API     : http://localhost:8000/docs
echo.
start http://localhost:3000
