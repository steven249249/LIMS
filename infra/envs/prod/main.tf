terraform {
  required_version = ">= 1.7"

  backend "gcs" {
    # Created manually before first `terraform init`. See infra/README.md.
    bucket = "lims-tfstate-prod"
    prefix = "infra"
  }

  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "lims-prod"
  namespace   = "lims-prod"
}

# 1. Network — VPC, NAT, PSA range, ingress static IP
module "network" {
  source = "../../modules/network"

  name_prefix     = local.name_prefix
  region          = var.region
  gke_subnet_cidr = "10.10.0.0/20"
  pods_cidr       = "10.20.0.0/16"
  services_cidr   = "10.30.0.0/20"
}

# 2. Cluster — GKE Autopilot, regional, private nodes
module "gke" {
  source = "../../modules/gke"

  project_id          = var.project_id
  name_prefix         = local.name_prefix
  region              = var.region
  vpc_id              = module.network.vpc_id
  subnet_id           = module.network.gke_subnet_id
  authorized_networks = var.authorized_networks
  env                 = "prod"
}

# 3. Database — Cloud SQL for MySQL 8.
#    DEMO TIER (Scenario B):
#      tier              = db-custom-1-3840  (1 vCPU, 3.75 GiB → ~$50/mo)
#      availability_type = ZONAL              (no HA replica → save ~50%)
#      deletion_protection = false            (so terraform destroy works
#                                              when demo window ends)
#    For real production switch to db-custom-2-7680 + REGIONAL + true.
module "cloudsql" {
  source = "../../modules/cloudsql"

  name_prefix         = local.name_prefix
  region              = var.region
  vpc_id              = module.network.vpc_id
  env                 = "prod"
  tier                = "db-custom-1-3840"
  availability_type   = "ZONAL"
  deletion_protection = false
  psa_dependency      = module.network.psa_connection
}

# 4. Cache + Celery broker — Memorystore Redis.
#    DEMO TIER (Scenario B):
#      tier      = BASIC      (single-node, no replica → save ~50%)
#      memory_gb = 1          (~$40/mo)
#    Real prod: STANDARD_HA + 5 GB.
module "memorystore" {
  source = "../../modules/memorystore"

  name_prefix    = local.name_prefix
  region         = var.region
  vpc_id         = module.network.vpc_id
  psa_range_name = module.network.psa_range_name
  env            = "prod"
  tier           = "BASIC"
  memory_gb      = 1

  depends_on = [module.network]
}

# 5. Image registry — only created in this (prod) env, shared with the others
module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id = var.project_id
  region     = var.region
}

# 6. Identity — runtime SA + Workload Identity binding for app pods
#    + (only here, because shared) the CI builder SA + Workload Identity
#    Federation pool for GitHub Actions OIDC.
module "iam" {
  source = "../../modules/iam"

  project_id        = var.project_id
  region            = var.region
  name_prefix       = local.name_prefix
  namespace         = local.namespace
  enable_ci_builder = true                # <-- ONLY in prod
  github_org        = var.github_org
  github_repo       = var.github_repo
}

# Surfaces every value the Helm chart / DDNS / GitHub Actions need.
output "ingress_static_ip_address" { value = module.network.ingress_static_ip_address }
output "ingress_static_ip_name"    { value = module.network.ingress_static_ip_name }
output "cluster_name"              { value = module.gke.cluster_name }
output "cloudsql_connection_name"  { value = module.cloudsql.connection_name }
output "redis_url"                 { value = module.memorystore.redis_url, sensitive = true }
output "artifact_registry_path"    { value = module.artifact_registry.repository_path }
output "runtime_gsa_email"         { value = module.iam.runtime_gsa_email }
output "ci_builder_email"          { value = module.iam.ci_builder_email }
output "wif_provider_resource"     { value = module.iam.wif_provider_resource }
