# Start Local Agentic AI Server & Ngrok Tunnel for GitHub Webhooks
Write-Host "=== Starting Agentic AI Server & Ngrok Tunnel ===" -ForegroundColor Cyan

# 1. Start Server on Port 8085 if not running
$serverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn dashboard.backend.main:app*" }
if (-not $serverProcess) {
    Write-Host "Starting FastAPI Backend Server on port 8085..." -ForegroundColor Green
    Start-Process -FilePath "python" -ArgumentList "-m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8085" -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "Backend Server is already running on port 8085." -ForegroundColor Yellow
}

# 2. Launch Ngrok Tunnel on Port 8085
Write-Host "Launching ngrok http 8085..." -ForegroundColor Green
ngrok http 8085
