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
