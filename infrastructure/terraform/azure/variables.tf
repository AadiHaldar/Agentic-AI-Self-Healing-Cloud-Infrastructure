variable "resource_group_name" {
  type        = string
  description = "Name of the Azure Resource Group."
  default     = "rg-agentic-cloud-prod"
}

variable "location" {
  type        = string
  description = "Azure Region for all resources."
  default     = "eastasia"
}

variable "cluster_name" {
  type        = string
  description = "Name of the Azure Kubernetes Service (AKS) cluster."
  default     = "aks-agentic-cloud"
}

variable "node_count" {
  type        = number
  description = "Number of worker nodes in the default AKS node pool."
  default     = 2
}

variable "vm_size" {
  type        = string
  description = "Virtual Machine size for the AKS node pool."
  default     = "Standard_D2s_v5"
}

variable "acr_name" {
  type        = string
  description = "Name of the Azure Container Registry (must be globally unique, alphanumeric only)."
  default     = "acragenticai2026"
}

variable "environment" {
  type        = string
  description = "Deployment environment tag (dev, staging, prod)."
  default     = "production"
}

# ── Container Apps ────────────────────────────────────────────────────────────

variable "container_app_name" {
  type        = string
  description = "Name of the Azure Container App (also used as suffix for related resources)."
  default     = "pr-review-agent"
}

# ── Key Vault ─────────────────────────────────────────────────────────────────

variable "key_vault_name" {
  type        = string
  description = "Globally unique Key Vault name (3-24 alphanumeric + hyphens)."
  default     = "kv-agentic-ai-2026"
}

# Sensitive vars — supply via TF_VAR_* environment variables or a .tfvars file
# (never commit real values to source control).
variable "gemini_api_key" {
  type        = string
  description = "Google Gemini API key (injected at deploy time)."
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_CI"
}

variable "github_app_private_key" {
  type        = string
  description = "Base64-encoded GitHub App RSA private key PEM."
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_CI"
}

variable "github_webhook_secret" {
  type        = string
  description = "GitHub App webhook HMAC secret."
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_CI"
}

# ── PostgreSQL ────────────────────────────────────────────────────────────────

variable "postgres_sku" {
  type        = string
  description = "PostgreSQL Flexible Server SKU tier (e.g. B_Standard_B1ms for dev, GP_Standard_D2s_v3 for prod)."
  default     = "B_Standard_B1ms"
}

variable "postgres_admin" {
  type        = string
  description = "PostgreSQL administrator login name."
  default     = "pgadmin"
}

variable "postgres_password" {
  type        = string
  description = "PostgreSQL administrator password."
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_CI"
}

variable "postgres_db_name" {
  type        = string
  description = "Name of the application database on the PostgreSQL server."
  default     = "pr_review_agent"
}
