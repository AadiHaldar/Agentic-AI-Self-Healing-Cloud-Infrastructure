<#
.SYNOPSIS
  Starts everything needed for the LIVE PR-review demo on this laptop.

.DESCRIPTION
  1. Relay window : smee.io -> http://127.0.0.1:8000/webhooks/github (GitHub cannot reach a laptop directly,
                    so GitHub delivers webhooks to the smee channel and this client forwards them).
  2. Server window: the AgentHeal API + console with the GitHub App credentials already stored in data/ and .env.
                    Its terminal shows the review pipeline running in real time - keep it visible on screen.
  3. Opens the console and the GitHub "Open a pull request" form for the prepared demo branch.

  Run from anywhere:  powershell -ExecutionPolicy Bypass -File scripts\live_demo.ps1
#>
param(
    [string]$Relay = "https://smee.io/bnQuJsrvp8I1iUA",
    [string]$Repo = "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
    [string]$DemoBranch = "demo/live-review",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Warning "Port 8000 is already in use (an old server?). Stop it first, then re-run."
    Write-Host   "  Find it:  Get-NetTCPConnection -LocalPort 8000 -State Listen | Select OwningProcess"
    exit 1
}

# Child windows inherit these.
$env:PYTHONPATH        = $root
$env:SEED_DEMO_DATA    = "0"        # no fabricated review history: only real reviews appear
$env:WEBHOOK_PROXY_URL = $Relay
$env:AUTOFIX_RUN_TESTS  = "1"        # auto-fix runs the tests it generates (executes model-written code; demo host only)

Write-Host "Starting relay window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'RELAY  smee -> :8000'; npx --yes smee-client --url $Relay --target http://127.0.0.1:8000/webhooks/github"

Write-Host "Starting server window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'AGENTHEAL SERVER'; Set-Location '$root'; python -m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8000 --no-access-log"

Write-Host "Waiting for the server..." -NoNewline
$meta = $null
for ($i = 0; $i -lt 45; $i++) {
    try { $meta = Invoke-RestMethod "http://127.0.0.1:8000/api/meta" -TimeoutSec 2; break }
    catch { Start-Sleep -Seconds 2; Write-Host "." -NoNewline }
}
Write-Host ""
if (-not $meta) { Write-Warning "Server did not come up. Check the server window for errors."; exit 1 }

Write-Host ""
Write-Host "READY" -ForegroundColor Green
Write-Host ("  Gemini connected   : {0}" -f $meta.gemini_configured)
Write-Host ("  PR-review webhook  : {0}" -f $meta.github_pr_review_mounted)
Write-Host ("  Cluster reachable  : {0}" -f $meta.cluster_reachable)
Write-Host "  Relay channel      : $Relay"
Write-Host ""
Write-Host "Demo: open a PR from branch '$DemoBranch' into main, then watch the SERVER window and the PR page."

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:8000/#/overview"
    Start-Process "https://github.com/$Repo/compare/main...${DemoBranch}?expand=1"
}
