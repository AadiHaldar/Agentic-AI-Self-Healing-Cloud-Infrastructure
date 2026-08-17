variable "resource_group_name" {
  type        = string
  description = "Name of the Azure Resource Group."
  default     = "rg-agentic-cloud-prod"
}

variable "location" {
  type        = string
  description = "Azure Region for all resources."
  default     = "eastus"
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
