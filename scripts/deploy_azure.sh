#!/usr/bin/env bash
# ==============================================================================
# 1-Click Azure Deployment Script for Agentic AI Cloud Platform
# ==============================================================================
set -euo pipefail

RG_NAME="${1:-rg-agentic-cloud-prod}"
LOCATION="${2:-eastus}"
CLUSTER_NAME="${3:-aks-agentic-cloud}"
ACR_NAME="${4:-acragenticai2026}"

echo "================================================================"
echo " Agentic AI Cloud Infrastructure — Azure 1-Click Deployment     "
echo "================================================================"

# 1. Check Azure Login
echo -e "\n[1/6] Checking Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
    echo "  [!] Not logged in. Running 'az login'..."
    az login
fi

# 2. Provision Infrastructure via Terraform
echo -e "\n[2/6] Provisioning Azure Infrastructure via Terraform..."
cd infrastructure/terraform/azure
terraform init
terraform apply -auto-approve \
    -var="resource_group_name=${RG_NAME}" \
    -var="location=${LOCATION}" \
    -var="cluster_name=${CLUSTER_NAME}" \
    -var="acr_name=${ACR_NAME}"

ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
AKS_NAME=$(terraform output -raw aks_cluster_name)
RG=$(terraform output -raw resource_group_name)
cd ../../..

# 3. Get AKS Credentials
echo -e "\n[3/6] Configuring kubectl credentials for AKS..."
az aks get-credentials --resource-group "${RG}" --name "${AKS_NAME}" --overwrite-existing

# 4. Build and Push Container Image to ACR
echo -e "\n[4/6] Building and pushing container image to ACR (${ACR_LOGIN_SERVER})..."
az acr build --registry "${ACR_NAME}" --image agentic-ai-platform:latest .

# 5. Create Namespace and Secrets
echo -e "\n[5/6] Creating Kubernetes namespace and secrets..."
kubectl create namespace agentic-ai --dry-run=client -o yaml | kubectl apply -f -

if [ -f ".env" ]; then
    kubectl create secret generic agentic-secrets \
        --from-env-file=.env \
        --namespace=agentic-ai \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "  -> Injected secrets from .env"
else
    kubectl create secret generic agentic-secrets \
        --from-literal=GEMINI_API_KEY="" \
        --namespace=agentic-ai \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# 6. Deploy Applications
echo -e "\n[6/6] Deploying Microservices and Agentic AI Platform..."
kubectl apply -f infrastructure/k8s/app/online-boutique.yaml

sed "s|acragenticai2026.azurecr.io|${ACR_LOGIN_SERVER}|g" infrastructure/k8s/app/agentic-ai-platform.yaml | kubectl apply -f -

echo "================================================================"
echo " Azure Deployment Completed Successfully!                      "
echo "================================================================"
echo "Watching for Azure LoadBalancer public IP:"
kubectl get service agentic-ai-service -n agentic-ai -w
