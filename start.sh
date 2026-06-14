#!/bin/bash
echo "Starting TradeDataLakePJ..."

if ! docker info > /dev/null 2>&1; then
    echo "Docker Desktop is not running. Starting it..."
    open -a "Docker"

    echo "Waiting for Docker to start (up to 60 seconds)..."
    count=0
    while ! docker info > /dev/null 2>&1; do
        sleep 3
        count=$((count + 3))
        if [ $count -ge 60 ]; then
            echo "Docker Desktop did not start in time. Please start it manually and retry."
            exit 1
        fi
    done
fi

docker compose up -d
if [ $? -ne 0 ]; then
    echo "Failed to start containers."
    exit 1
fi

echo "Waiting for Grafana to be ready..."
count=0
while true; do
    sleep 3
    count=$((count + 3))
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null)
    if [ "$status" = "200" ]; then
        break
    fi
    if [ $count -ge 60 ]; then
        echo "Grafana did not respond in time. Opening anyway..."
        break
    fi
done

echo ""
echo " Started successfully."
echo "   Dashboard : http://localhost:3000/d/daytrade-v1"
echo "   API       : http://localhost:8000/docs"
echo ""
open "http://localhost:3000/d/daytrade-v1"
