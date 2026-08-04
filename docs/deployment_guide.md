# Deployment & User Guide

This guide covers running the **Agentic AI Self-Healing Infrastructure** both locally (free development mode) and on **Azure AKS** (production cloud mode using Azure free credits).

---

## 1. Local Deployment (Free RTX 5060 / Local Workstation)

### Prerequisites:
- Docker Desktop (with Kubernetes enabled) OR Minikube / K3s
- Python 3.10+
- kubectl & Helm

### Quickstart Steps:

1. **Deploy Kubernetes Infrastructure (Prometheus, Grafana, Loki, Chaos Mesh, Online Boutique):**
   ```powershell
   .\scripts\setup_local.ps1
   ```

2. **Install Python Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Start the Dashboard Backend API & Web Server:**
   ```powershell
   python -m uvicorn dashboard.backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the Web Dashboard:**
   Open your browser and navigate to: `http://localhost:8000/`

---

## 2. Azure Cloud Deployment (Azure AKS)

### Prerequisites:
- Azure CLI (`az login`)
- Terraform

### Cloud Provisioning Steps:

1. **Authenticate with Azure:**
   ```bash
   az login
   ```

2. **Deploy AKS Cluster via Terraform:**
   ```bash
   cd infrastructure/terraform/azure
   terraform init
   terraform apply -auto-approve
   ```

3. **Connect `kubectl` to Azure AKS:**
   ```bash
   az aks get-credentials --resource-group agentic-cloud-rg --name agentic-aks-cluster
   ```

4. **Deploy Application & Monitoring Stack to AKS:**
   ```powershell
   .\scripts\setup_local.ps1
   ```

---

## 3. Running System Evaluation & Benchmarks

To execute the automated end-to-end evaluation suite measuring **MTTD**, **MTTR**, and **Parallel Agent Divergence**:

```powershell
python -m unittest tests/e2e_evaluation.py
```
