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

echo Waiting for Grafana to be ready...
set /a count=0
:wait_grafana
timeout /t 3 /nobreak >nul
set /a count+=3
curl -s -o nul -w "%%{http_code}" http://localhost:3000/api/health | findstr "200" >nul 2>&1
if %ERRORLEVEL% equ 0 goto grafana_ready
if %count% lss 60 goto wait_grafana
echo Grafana did not respond in time. Opening anyway...

:grafana_ready
echo.
echo Started successfully.
echo   Dashboard: http://localhost:3000/d/daytrade-v1
echo   API      : http://localhost:8000/docs
echo.
start http://localhost:3000/d/daytrade-v1
