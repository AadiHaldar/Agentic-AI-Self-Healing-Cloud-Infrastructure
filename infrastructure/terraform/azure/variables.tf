variable "resource_group_name" {
  type        = string
  description = "Name of the resource group."
  default     = "agentic-cloud-rg"
}

variable "location" {
  type        = string
  description = "Azure Region."
  default     = "East US"
}

variable "cluster_name" {
  type        = string
  description = "Name of the AKS cluster."
  default     = "agentic-aks-cluster"
}

variable "node_count" {
  type        = number
  description = "Number of worker nodes in the cluster."
  default     = 3
}

variable "vm_size" {
  type        = string
  description = "Size of the VMs."
  default     = "Standard_D2_v2"
}
