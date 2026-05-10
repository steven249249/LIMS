terraform {
  required_version = ">= 1.7"
  backend "gcs" {
    bucket = "lims-tfstate-dev"
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
  name_prefix = "lims-dev"
  namespace   = "lims-dev"
}

module "network" {
  source          = "../../modules/network"
  name_prefix     = local.name_prefix
  region          = var.region
  gke_subnet_cidr = "10.110.0.0/20"
  pods_cidr       = "10.120.0.0/16"
  services_cidr   = "10.130.0.0/20"
}

module "gke" {
  source              = "../../modules/gke"
  project_id          = var.project_id
  name_prefix         = local.name_prefix
  region              = var.region
  vpc_id              = module.network.vpc_id
  subnet_id           = module.network.gke_subnet_id
  authorized_networks = var.authorized_networks
  env                 = "dev"
}

module "cloudsql" {
  source         = "../../modules/cloudsql"
  name_prefix    = local.name_prefix
  region         = var.region
  vpc_id         = module.network.vpc_id
  env            = "dev"
  tier           = "db-f1-micro"
  psa_dependency = module.network.psa_connection
}

module "memorystore" {
  source         = "../../modules/memorystore"
  name_prefix    = local.name_prefix
  region         = var.region
  vpc_id         = module.network.vpc_id
  psa_range_name = module.network.psa_range_name
  env            = "dev"
  memory_gb      = 1
  depends_on     = [module.network]
}

# IAM: runtime SA only. The shared CI builder + WIF pool live in the
# prod env (enable_ci_builder = true there).
module "iam" {
  source            = "../../modules/iam"
  project_id        = var.project_id
  region            = var.region
  name_prefix       = local.name_prefix
  namespace         = local.namespace
  enable_ci_builder = false
}

output "ingress_static_ip_address" { value = module.network.ingress_static_ip_address }
output "ingress_static_ip_name"    { value = module.network.ingress_static_ip_name }
output "cluster_name"              { value = module.gke.cluster_name }
output "cloudsql_connection_name"  { value = module.cloudsql.connection_name }
output "redis_url"                 { value = module.memorystore.redis_url, sensitive = true }
output "runtime_gsa_email"         { value = module.iam.runtime_gsa_email }
