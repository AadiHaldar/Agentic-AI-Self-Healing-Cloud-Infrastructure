output "kube_config" {
  value       = azurerm_kubernetes_cluster.aks_cluster.kube_config_raw
  sensitive   = true
  description = "Kubeconfig for the AKS cluster"
}

output "cluster_name" {
  value       = azurerm_kubernetes_cluster.aks_cluster.name
  description = "The name of the AKS cluster"
}
