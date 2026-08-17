output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "The name of the Azure Resource Group."
}

# output "aks_cluster_name" { ... }
# output "aks_get_credentials_command" { ... }

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
