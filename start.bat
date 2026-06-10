@echo off
echo Starting TradeDataLakePJ...

docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Docker Desktop is not running. Starting it...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to start (up to 60 seconds)...
    set /a count=0
    :wait_loop
    timeout /t 3 /nobreak >nul
    set /a count+=3
    docker info >nul 2>&1
    if %ERRORLEVEL% equ 0 goto docker_ready
    if %count% lss 60 goto wait_loop
    echo Docker Desktop did not start in time. Please start it manually and retry.
    pause
    exit /b 1
)

:docker_ready
docker compose up -d
if %ERRORLEVEL% neq 0 (
    echo Failed to start containers.
    pause
    exit /b 1
)
echo.
echo Started successfully.
echo   Grafana : http://localhost:3000  (admin / admin)
echo   API     : http://localhost:8000/docs
echo.
start http://localhost:3000
