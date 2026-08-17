output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "The name of the Azure Resource Group."
}

output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "The name of the AKS cluster."
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "Login server endpoint for Azure Container Registry."
}

output "acr_admin_username" {
  value       = azurerm_container_registry.acr.admin_username
  description = "Admin username for ACR."
  sensitive   = true
}

output "acr_admin_password" {
  value       = azurerm_container_registry.acr.admin_password
  description = "Admin password for ACR."
  sensitive   = true
}

output "aks_get_credentials_command" {
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name} --overwrite-existing"
  description = "CLI command to connect kubectl to the newly provisioned AKS cluster."
}

# ── Container Apps outputs ────────────────────────────────────────────────────

output "container_app_fqdn" {
  value       = "https://${azurerm_container_app.pr_review_agent.latest_revision_fqdn}"
  description = "Stable HTTPS URL for the Container App — use this as the GitHub App webhook base URL."
}

output "webhook_url" {
  value       = "https://${azurerm_container_app.pr_review_agent.latest_revision_fqdn}/webhooks/github"
  description = "Fully-qualified GitHub webhook endpoint to register in the GitHub App settings."
}

output "install_url" {
  value       = "https://${azurerm_container_app.pr_review_agent.latest_revision_fqdn}/install"
  description = "GitHub App manifest-flow install page URL."
}

# ── Key Vault outputs ─────────────────────────────────────────────────────────

output "key_vault_uri" {
  value       = azurerm_key_vault.kv.vault_uri
  description = "Azure Key Vault URI for manual secret management."
}

output "key_vault_name" {
  value       = azurerm_key_vault.kv.name
  description = "Azure Key Vault name."
}

# ── PostgreSQL outputs ────────────────────────────────────────────────────────

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.db.fqdn
  description = "PostgreSQL Flexible Server FQDN (use in DATABASE_URL)."
}

output "database_url_template" {
  value       = "postgresql+asyncpg://${var.postgres_admin}:***@${azurerm_postgresql_flexible_server.db.fqdn}/${var.postgres_db_name}?ssl=require"
  description = "DATABASE_URL template (password redacted). Actual value is stored in Key Vault."
}
