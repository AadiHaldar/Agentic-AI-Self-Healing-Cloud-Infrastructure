<#
.SYNOPSIS
    Automated 1-Click Production Deployment to Microsoft Azure AKS & ACR.
.DESCRIPTION
    Provisions Azure Resource Group, ACR, Log Analytics, and AKS via Terraform,
    builds the production container image in ACR, and deploys the microservice testbed
    along with the Agentic AI Self-Healing & PR Review Platform.
#>

param (
    [string]$ResourceGroupName = "rg-agentic-cloud-prod",
    [string]$Location = "eastus",
    [string]$ClusterName = "aks-agentic-cloud",
    [string]$AcrName = "acragenticai2026"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Agentic AI Cloud Infrastructure — Azure 1-Click Deployment     " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Verify Azure CLI login
Write-Host "`n[1/6] Checking Azure CLI authentication..." -ForegroundColor Yellow
try {
    $account = az account show --output json | ConvertFrom-Json
    Write-Host "  -> Logged in as: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green
} catch {
    Write-Host "  [!] Not logged into Azure. Running 'az login'..." -ForegroundColor Red
    az login
}

# 2. Provision Infrastructure via Terraform
Write-Host "`n[2/6] Provisioning Azure Infrastructure via Terraform..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot/../infrastructure/terraform/azure"

terraform init
terraform apply -auto-approve `
    -var="resource_group_name=$ResourceGroupName" `
    -var="location=$Location" `
    -var="cluster_name=$ClusterName" `
    -var="acr_name=$AcrName"

$acrLoginServer = terraform output -raw acr_login_server
$aksName = terraform output -raw aks_cluster_name
$rgName = terraform output -raw resource_group_name

Pop-Location

# 3. Connect kubectl to AKS
Write-Host "`n[3/6] Configuring kubectl credentials for AKS..." -ForegroundColor Yellow
az aks get-credentials --resource-group $rgName --name $aksName --overwrite-existing

# 4. Build and Push Container Image to ACR (Cloud Build)
Write-Host "`n[4/6] Building and pushing container image to ACR ($acrLoginServer)..." -ForegroundColor Yellow
az acr build --registry $AcrName --image agentic-ai-platform:latest .

# 5. Create Kubernetes Secrets from .env if present
Write-Host "`n[5/6] Creating Kubernetes namespace and secrets..." -ForegroundColor Yellow
kubectl create namespace agentic-ai --dry-run=client -o yaml | kubectl apply -f -

if (Test-Path ".env") {
    kubectl create secret generic agentic-secrets `
        --from-env-file=.env `
        --namespace=agentic-ai `
        --dry-run=client -o yaml | kubectl apply -f -
    Write-Host "  -> Injected secrets from .env" -ForegroundColor Green
} else {
    kubectl create secret generic agentic-secrets `
        --from-literal=GEMINI_API_KEY="" `
        --namespace=agentic-ai `
        --dry-run=client -o yaml | kubectl apply -f -
    Write-Host "  -> Created empty agentic-secrets (update later with kubectl)" -ForegroundColor Yellow
}

# 6. Deploy Applications and Microservice Testbed
Write-Host "`n[6/6] Deploying Microservices and Agentic AI Platform..." -ForegroundColor Yellow

# Deploy Online Boutique microservices
kubectl apply -f infrastructure/k8s/app/online-boutique.yaml

# Deploy Agentic AI Platform control plane
# Replace placeholder ACR name with actual ACR login server
$manifest = Get-Content infrastructure/k8s/app/agentic-ai-platform.yaml -Raw
$manifest = $manifest -replace "acragenticai2026.azurecr.io", $acrLoginServer
$manifest | kubectl apply -f -

Write-Host "`n================================================================" -ForegroundColor Green
Write-Host " Azure Deployment Completed Successfully!                      " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "`nChecking Service Public IP (may take 1-2 minutes for Azure LoadBalancer):"
kubectl get service agentic-ai-service -n agentic-ai -w
