# ==============================================================================
# Terraform Azure Infrastructure for Agentic AI Self-Healing Cloud Platform
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
    ManagedBy   = "Terraform"
  }
}

# 2. Azure Container Registry (ACR)
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# 3. Log Analytics Workspace for Container Insights
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "law-${var.cluster_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# 4. (Optional) AKS Cluster — Commented out to prevent student VM quota limits (Azure Container Apps is used instead)
# resource "azurerm_kubernetes_cluster" "aks" { ... }
# resource "azurerm_role_assignment" "aks_acr_pull" { ... }

