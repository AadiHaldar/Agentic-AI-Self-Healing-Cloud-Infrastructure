# ==============================================================================
# Azure Container Apps — Agentic AI Self-Healing PR Review Agent
#
# Resources provisioned:
#   1. Log Analytics Workspace (shared with AKS if desired)
#   2. Container Apps Environment
#   3. Container App (pr-review-agent service)
#   4. Azure Key Vault (secrets: Gemini API key, GitHub App PEM, webhook secret)
#   5. Managed Identity → ACR AcrPull + Key Vault Secrets User roles
#   6. PostgreSQL Flexible Server (DATABASE_URL scaffolded, ready for migration)
#
# The Container App is the primary stable webhook endpoint for GitHub App.
# It scales to zero when idle, drastically reducing cost vs AKS.
# ==============================================================================

# ── Managed Identity ──────────────────────────────────────────────────────────

resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "id-${var.container_app_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# ── Log Analytics Workspace ───────────────────────────────────────────────────
# Reuse the one created in main.tf if it exists, or create a dedicated one.

resource "azurerm_log_analytics_workspace" "aca_logs" {
  name                = "law-aca-${var.container_app_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# ── Container Apps Environment ────────────────────────────────────────────────

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${var.container_app_name}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.aca_logs.id

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# ── Container App ─────────────────────────────────────────────────────────────

resource "azurerm_container_app" "pr_review_agent" {
  name                         = var.container_app_name
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  # Managed identity gives the app pull access to ACR and read access to Key Vault
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app_identity.id]
  }

  # Pull image from ACR using the managed identity (no admin credentials needed)
  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app_identity.id
  }

  template {
    min_replicas = 0   # scale to zero when idle
    max_replicas = 5   # burst capacity

    # Scale rule: scale up based on concurrent HTTP requests
    http_scale_rule {
      name                = "http-scale"
      concurrent_requests = "10"
    }

    container {
      name   = "pr-review-agent"
      image  = "${azurerm_container_registry.acr.login_server}/${var.container_app_name}:latest"
      cpu    = 0.5
      memory = "1Gi"

      # Runtime secrets pulled from Key Vault at startup via managed identity
      env {
        name        = "GEMINI_API_KEY"
        secret_name = "gemini-api-key"
      }
      env {
        name        = "GITHUB_APP_PRIVATE_KEY"
        secret_name = "github-app-private-key"
      }
      env {
        name        = "GITHUB_WEBHOOK_SECRET"
        secret_name = "github-webhook-secret"
      }
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "PORT"
        value = "8000"
      }
      env {
        name  = "PYTHONUNBUFFERED"
        value = "1"
      }

      # Liveness / readiness probe
      liveness_probe {
        path             = "/api/status"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 15
        interval_seconds = 30
        timeout          = 5
        failure_count_threshold = 3
      }
      readiness_probe {
        path             = "/api/service-health"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 5
        interval_seconds = 10
        timeout          = 3
        failure_count_threshold = 2
      }
    }
  }

  # Secrets are mounted from Key Vault via managed identity
  secret {
    name                = "gemini-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.gemini_api_key.id
    identity            = azurerm_user_assigned_identity.app_identity.id
  }
  secret {
    name                = "github-app-private-key"
    key_vault_secret_id = azurerm_key_vault_secret.github_app_private_key.id
    identity            = azurerm_user_assigned_identity.app_identity.id
  }
  secret {
    name                = "github-webhook-secret"
    key_vault_secret_id = azurerm_key_vault_secret.github_webhook_secret.id
    identity            = azurerm_user_assigned_identity.app_identity.id
  }
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.database_url.id
    identity            = azurerm_user_assigned_identity.app_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# ── ACR AcrPull for managed identity ─────────────────────────────────────────

resource "azurerm_role_assignment" "app_acr_pull" {
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.acr.id
}

# ── Azure Key Vault ───────────────────────────────────────────────────────────

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Soft delete prevents accidental key loss
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  # Allow Terraform provisioner to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
  }

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

# Grant managed identity read access to Key Vault secrets
resource "azurerm_key_vault_access_policy" "app_identity_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.app_identity.principal_id

  secret_permissions = ["Get", "List"]
}

# Secret placeholders — real values injected via CI/CD or manually post-init
resource "azurerm_key_vault_secret" "gemini_api_key" {
  name         = "gemini-api-key"
  value        = var.gemini_api_key
  key_vault_id = azurerm_key_vault.kv.id

  lifecycle {
    ignore_changes = [value]   # managed out-of-band after first apply
  }
}

resource "azurerm_key_vault_secret" "github_app_private_key" {
  name         = "github-app-private-key"
  value        = var.github_app_private_key
  key_vault_id = azurerm_key_vault.kv.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "github_webhook_secret" {
  name         = "github-webhook-secret"
  value        = var.github_webhook_secret
  key_vault_id = azurerm_key_vault.kv.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = "postgresql+asyncpg://${var.postgres_admin}:${var.postgres_password}@${azurerm_postgresql_flexible_server.db.fqdn}/${var.postgres_db_name}?ssl=require"
  key_vault_id = azurerm_key_vault.kv.id

  lifecycle {
    ignore_changes = [value]
  }
}

# ── PostgreSQL Flexible Server (DATABASE_URL scaffolding) ─────────────────────
# db.py currently uses SQLite; this Postgres server is provisioned now so the
# DATABASE_URL env var is ready when the SQLAlchemy migration lands.

resource "azurerm_postgresql_flexible_server" "db" {
  name                   = "psql-${var.container_app_name}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  administrator_login    = var.postgres_admin
  administrator_password = var.postgres_password
  storage_mb             = 32768
  sku_name               = var.postgres_sku

  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }

  tags = {
    Environment = var.environment
    Project     = "Agentic-AI-Self-Healing-Cloud"
  }
}

resource "azurerm_postgresql_flexible_server_database" "app_db" {
  name      = var.postgres_db_name
  server_id = azurerm_postgresql_flexible_server.db.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Allow Container Apps egress IPs to connect (Azure services rule)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.db.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
