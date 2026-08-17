# Microsoft Azure Cloud Deployment Guide

This guide provides end-to-end instructions for deploying the **Agentic AI Self-Healing Cloud Infrastructure & Autonomous PR Review Platform** onto **Microsoft Azure** using Azure Kubernetes Service (AKS), Azure Container Registry (ACR), and Terraform.

---

## 1. Architecture Overview on Azure

```
                                          ┌────────────────────────────────────────┐
                                          │          Azure Cloud Platform          │
                                          │                                        │
  [Developer / GitHub PR]                │   ┌────────────────────────────────┐   │
             │                            │   │ Azure Container Registry (ACR) │   │
             ▼ Webhook HTTPS              │   │ (OCI Container Images)         │   │
┌───────────────────────────────┐         │   └───────────────┬────────────────┘   │
│ Azure LoadBalancer (Public IP)│─────────┼───────────────────┼────────────────────┤
└───────────────┬───────────────┘         │                   ▼                    │
                │                         │   ┌────────────────────────────────┐   │
                ▼                         │   │ Azure Kubernetes Service (AKS) │   │
  ┌───────────────────────────┐           │   │                                │   │
  │ agentic-ai-service (:80)  │           │   │  Namespace: agentic-ai         │   │
  └─────────────┬─────────────┘           │   │  ├─ agentic-ai-platform        │   │
                │                         │   │  │  ├─ React/Vite UI (:8000)   │   │
                ▼                         │   │  │  ├─ FastAPI Backend (:8000) │   │
  ┌───────────────────────────┐           │   │  │  └─ SimPy + Gemini ReAct    │   │
  │ agentic-ai-platform (Pod) │           │   │  └─ agentic-db-pvc (5Gi Azure) │   │
  └─────────────┬─────────────┘           │   │                                │   │
                │ Ingest & Control        │   │  Namespace: default            │   │
                ▼                         │   │  ├─ Online Boutique 11 Svc     │   │
  ┌───────────────────────────┐           │   │  └─ Chaos Mesh Operators       │   │
  │ Microservices + ChaosMesh │           │   └────────────────────────────────┘   │
  └───────────────────────────┘           └────────────────────────────────────────┘
```

---

## 2. Prerequisites

1. **Azure CLI (`az`)**: [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Terraform (>= 1.5.0)**: [Install Terraform](https://developer.hashicorp.com/terraform/install)
3. **Kubernetes CLI (`kubectl`)**: [Install kubectl](https://kubernetes.io/docs/tasks/tools/)
4. **Active Azure Subscription**: (Azure Free Account or Student Subscription)

---

## 3. Automated 1-Click Deployment

Run the automated script corresponding to your operating system from the root repository directory:

### Windows (PowerShell):
```powershell
.\scripts\deploy_azure.ps1 -ResourceGroupName "rg-agentic-cloud-prod" -Location "eastus" -ClusterName "aks-agentic-cloud" -AcrName "acragenticai2026"
```

### Linux / macOS (Bash):
```bash
chmod +x ./scripts/deploy_azure.sh
./scripts/deploy_azure.sh "rg-agentic-cloud-prod" "eastus" "aks-agentic-cloud" "acragenticai2026"
```

---

## 4. Manual Step-by-Step Deployment

### Step 1: Authenticate with Azure
```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"
```

### Step 2: Provision Infrastructure with Terraform
```bash
cd infrastructure/terraform/azure
terraform init
terraform apply -auto-approve
```
*Note the output values: `acr_login_server`, `aks_cluster_name`, `resource_group_name`.*

### Step 3: Configure `kubectl` to target AKS
```bash
az aks get-credentials --resource-group rg-agentic-cloud-prod --name aks-agentic-cloud --overwrite-existing
```

### Step 4: Build and Push Docker Image to ACR
ACR provides cloud-native build agents so you do not need Docker running locally:
```bash
# From the project root
az acr build --registry acragenticai2026 --image agentic-ai-platform:latest .
```

### Step 5: Inject Secrets & Environment Configuration
```bash
kubectl create namespace agentic-ai --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic agentic-secrets \
  --from-literal=GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>" \
  --from-literal=GITHUB_TOKEN="<YOUR_GITHUB_PAT>" \
  --from-literal=GITHUB_APP_ID="4614506" \
  --namespace=agentic-ai
```

### Step 6: Deploy Microservice Testbed and Control Plane
```bash
# 1. Deploy Online Boutique microservices
kubectl apply -f infrastructure/k8s/app/online-boutique.yaml

# 2. Deploy Agentic AI Platform
kubectl apply -f infrastructure/k8s/app/agentic-ai-platform.yaml
```

### Step 7: Access the Live Dashboard
```bash
kubectl get service agentic-ai-service -n agentic-ai -w
```
Once the `EXTERNAL-IP` transitions from `<pending>` to a public IP (e.g. `20.120.45.67`), open your browser:
```
http://<EXTERNAL-IP>/
```

---

## 5. Fault Injection & Self-Healing Verification

To trigger a live simulated anomaly on Azure AKS and observe the Agentic AI remediation loop:

1. **Install Chaos Mesh on AKS**:
   ```bash
   curl -sSL https://mirrors.chaos-mesh.org/v2.6.2/install.sh | bash
   ```
2. **Inject CPU Congestion into CheckoutService**:
   ```bash
   kubectl apply -f infrastructure/k8s/chaos-mesh/cpu-stress.yaml
   ```
3. **Observe Self-Healing Action**:
   - The Digital Twin detects CPU anomaly (>85%).
   - SimPy executes a 0.01s dry-run simulation.
   - The Gemini ReAct / SimiFed RL agent executes `kubectl scale` or `restart_pod`.
   - The React Dashboard displays the live recovery timeline and SHAP attribution bars.

---

## 6. Cost Optimization & Teardown

To stop charges when you finish testing:
```bash
cd infrastructure/terraform/azure
terraform destroy -auto-approve
```
