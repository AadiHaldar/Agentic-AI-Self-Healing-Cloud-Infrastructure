# Azure Deployment — Bootstrap Guide

This guide walks through the **one-time setup** required to get the PR Review Agent running on **Azure Container Apps** with OIDC-based CI/CD, Key Vault secrets, and a PostgreSQL Flexible Server.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Azure CLI (`az`) | ≥ 2.57 |
| Terraform | ≥ 1.5 |
| Docker Desktop | ≥ 24 |
| GitHub CLI (`gh`) | ≥ 2.40 |

---

## Step 1 — Create the Azure Service Principal for OIDC

```bash
# Replace placeholders with your values
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Create service principal with Contributor scope
az ad app create --display-name "agentic-ai-github-actions"
APP_ID=$(az ad app list --display-name "agentic-ai-github-actions" --query "[0].appId" -o tsv)

az ad sp create --id $APP_ID
SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

az role assignment create \
  --role Contributor \
  --assignee-object-id $SP_OBJECT_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID
```

## Step 2 — Add Federated Credential (OIDC — no long-lived secrets)

```bash
# This allows GitHub Actions to authenticate via OIDC from the main branch.
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_ORG>/<YOUR_REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## Step 3 — Set GitHub Repository Secrets

```bash
gh secret set AZURE_CLIENT_ID       --body "$APP_ID"
gh secret set AZURE_TENANT_ID       --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"

# Application secrets (real values — never commit to code)
gh secret set GEMINI_API_KEY           --body "your-gemini-key"
gh secret set GITHUB_APP_PRIVATE_KEY   --body "base64-encoded-pem"
gh secret set GITHUB_WEBHOOK_SECRET    --body "your-webhook-secret"
gh secret set POSTGRES_PASSWORD        --body "strong-random-password"

# GitHub repo variables (non-sensitive, visible in Actions logs)
gh variable set AZURE_RESOURCE_GROUP   --body "rg-agentic-cloud-prod"
gh variable set ACR_NAME               --body "acragenticai2026"
gh variable set CONTAINER_APP_NAME     --body "pr-review-agent"
gh variable set TF_STATE_STORAGE_ACCOUNT --body "stterraformstate12345"
```

## Step 4 — Create Terraform Remote State Storage

```bash
RESOURCE_GROUP="rg-agentic-cloud-prod"
STORAGE_ACCOUNT="stterraformstate12345"   # must be globally unique

az group create --name $RESOURCE_GROUP --location eastus
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --sku Standard_LRS \
  --min-tls-version TLS1_2

az storage container create \
  --name tfstate \
  --account-name $STORAGE_ACCOUNT
```

## Step 5 — First Terraform Init & Apply (local bootstrap)

Run this once locally to provision all infrastructure before CI/CD takes over:

```bash
cd infrastructure/terraform/azure

terraform init \
  -backend-config="resource_group_name=rg-agentic-cloud-prod" \
  -backend-config="storage_account_name=stterraformstate12345" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=pr-review-agent.tfstate"

terraform plan \
  -var="gemini_api_key=your-gemini-key" \
  -var="github_app_private_key=base64-encoded-pem" \
  -var="github_webhook_secret=your-webhook-secret" \
  -var="postgres_password=strong-random-password"

terraform apply
```

After `apply`, Terraform prints outputs including:

```
container_app_fqdn = "https://pr-review-agent.happybeach-abc123.eastus.azurecontainerapps.io"
webhook_url        = "https://pr-review-agent.happybeach-abc123.eastus.azurecontainerapps.io/webhooks/github"
install_url        = "https://pr-review-agent.happybeach-abc123.eastus.azurecontainerapps.io/install"
key_vault_uri      = "https://kv-agentic-ai-2026.vault.azure.net/"
postgres_fqdn      = "psql-pr-review-agent.postgres.database.azure.com"
```

## Step 6 — Register the GitHub App

1. Open the `install_url` from Terraform output in a browser.
2. Click **"Install on GitHub"** — this runs the manifest flow and auto-configures:
   - App ID
   - Webhook secret
   - Private key PEM
3. The credentials are persisted to the SQLite DB and `.env.app` file inside the container.

> **Note:** The webhook URL used in the GitHub App registration will be the `webhook_url` from Step 5. This URL is stable — it doesn't change across Container App revisions.

## Step 7 — Trigger CI/CD (all future deploys)

Push to `main`:

```bash
git push origin main
```

The GitHub Actions workflow will:
1. Build the Docker image with `SKIP_FRONTEND=true`
2. Push to ACR
3. Run `terraform apply` (only if infra files changed)
4. Update the Container App revision (zero-downtime rolling deploy)
5. Hit `/api/service-health` to verify the new revision is healthy

---

## Architecture Diagram

```
GitHub Repository
       │  push to main
       ▼
GitHub Actions (OIDC)
  ├── docker build --build-arg SKIP_FRONTEND=true
  ├── docker push → ACR (acragenticai2026.azurecr.io)
  ├── terraform apply (infra changes only)
  └── az containerapp update → new revision

Azure Container Apps Environment
  └── Container App: pr-review-agent
       ├── Ingress: HTTPS → /webhooks/github, /install, /api/*
       ├── Scale: 0–5 replicas (HTTP concurrent-requests trigger)
       ├── Identity: User-Assigned Managed Identity
       │    ├── ACR AcrPull (pull images)
       │    └── Key Vault Secrets User (read secrets at startup)
       └── Secrets from Key Vault:
            ├── GEMINI_API_KEY
            ├── GITHUB_APP_PRIVATE_KEY
            ├── GITHUB_WEBHOOK_SECRET
            └── DATABASE_URL → PostgreSQL Flexible Server

Azure Key Vault (kv-agentic-ai-2026)
  └── Secrets: gemini-api-key, github-app-private-key,
               github-webhook-secret, database-url

Azure PostgreSQL Flexible Server (psql-pr-review-agent)
  └── Database: pr_review_agent
       └── Currently scaffolded — db.py uses SQLite
           DATABASE_URL is ready for the future migration
```

---

## Troubleshooting

### Container App startup failure

```bash
az containerapp logs show \
  --name pr-review-agent \
  --resource-group rg-agentic-cloud-prod \
  --follow
```

### Key Vault access denied

Verify managed identity has `Key Vault Secrets User` role:
```bash
az role assignment list \
  --assignee <managed-identity-principal-id> \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/kv-agentic-ai-2026
```

### Webhook signature failures

The `GITHUB_WEBHOOK_SECRET` in Key Vault must match the secret registered in the GitHub App settings. To rotate it:
1. Update the secret in GitHub App settings.
2. Update Key Vault: `az keyvault secret set --vault-name kv-agentic-ai-2026 --name github-webhook-secret --value "<new-secret>"`
3. Restart the Container App: `az containerapp revision restart --name pr-review-agent --resource-group rg-agentic-cloud-prod --revision <revision-name>`
