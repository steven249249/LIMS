terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

resource "google_redis_instance" "redis" {
  name           = "${var.name_prefix}-redis"
  tier           = var.tier
  memory_size_gb = var.memory_gb
  region         = var.region
  redis_version  = "REDIS_7_0"

  authorized_network = var.vpc_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  reserved_ip_range  = var.psa_range_name

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"
}

# Persist the AUTH string into Secret Manager so the app pod can read it
# via External Secrets Operator instead of a Terraform output.
resource "google_secret_manager_secret" "redis_auth" {
  secret_id = "${var.name_prefix}-redis-auth"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "redis_auth" {
  secret      = google_secret_manager_secret.redis_auth.id
  secret_data = google_redis_instance.redis.auth_string
}

# Helm consumes redis.url as a single string; assemble it here.
locals {
  redis_url = "redis://:${google_redis_instance.redis.auth_string}@${google_redis_instance.redis.host}:${google_redis_instance.redis.port}/0"
}

output "host"      { value = google_redis_instance.redis.host }
output "port"      { value = google_redis_instance.redis.port }
output "redis_url" { value = local.redis_url, sensitive = true }
