# deploy.ps1 — Quick deploy MTL Validator
# Usage: .\deploy.ps1 [docker|local|ngrok]

param([string]$mode = "local")

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

function Deploy-Local {
    Write-Host "[*] Starting local server..." -ForegroundColor Cyan
    Set-Location $projectRoot
    & python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

function Deploy-Docker {
    Write-Host "[*] Building Docker image..." -ForegroundColor Cyan
    docker build -t mtl-validator $projectRoot
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

    Write-Host "[*] Stopping old container..." -ForegroundColor Cyan
    docker rm -f mtl-validator 2>$null

    Write-Host "[*] Starting container on port 8000..." -ForegroundColor Cyan
    docker run -d -p 8000:8000 --name mtl-validator --restart unless-stopped mtl-validator

    Write-Host "[+] Done! API at http://localhost:8000" -ForegroundColor Green
    Write-Host "    Health: curl http://localhost:8000/api/v1/health"
    Write-Host "    OpenAPI (Dify): http://localhost:8000/dify/openapi.json"
}

function Deploy-Ngrok {
    Write-Host "[*] Starting local server..." -ForegroundColor Cyan
    Start-Process -NoNewWindow python -ArgumentList "-m","uvicorn","main:app","--host","0.0.0.0","--port","8000"
    Start-Sleep -Seconds 3

    Write-Host "[*] Starting ngrok tunnel..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    Command: ngrok http 8000" -ForegroundColor Yellow
    Write-Host "    → Then copy the ngrok URL (https://xxxx.ngrok-free.app)" -ForegroundColor Yellow
    Write-Host "    → Use that URL in Dify Tools > Import from OpenAPI:" -ForegroundColor Yellow
    Write-Host "      https://xxxx.ngrok-free.app/dify/openapi.json" -ForegroundColor White
    Write-Host ""
    ngrok http 8000
}

switch ($mode) {
    "local"  { Deploy-Local }
    "docker" { Deploy-Docker }
    "ngrok"  { Deploy-Ngrok }
    default {
        Write-Host "Usage: .\deploy.ps1 [local|docker|ngrok]" -ForegroundColor Red
        Write-Host "  local  - Run uvicorn directly (dev)" -ForegroundColor Gray
        Write-Host "  docker - Build & run Docker container" -ForegroundColor Gray
        Write-Host "  ngrok  - Run local + ngrok tunnel (for Dify test)" -ForegroundColor Gray
    }
}
