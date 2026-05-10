terraform {
  required_version = ">= 1.7"
  backend "gcs" {
    bucket = "lims-tfstate-staging"
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
  name_prefix = "lims-staging"
  namespace   = "lims-staging"
}

module "network" {
  source          = "../../modules/network"
  name_prefix     = local.name_prefix
  region          = var.region
  gke_subnet_cidr = "10.210.0.0/20"
  pods_cidr       = "10.220.0.0/16"
  services_cidr   = "10.230.0.0/20"
}

module "gke" {
  source              = "../../modules/gke"
  project_id          = var.project_id
  name_prefix         = local.name_prefix
  region              = var.region
  vpc_id              = module.network.vpc_id
  subnet_id           = module.network.gke_subnet_id
  authorized_networks = var.authorized_networks
  env                 = "staging"
}

module "cloudsql" {
  source         = "../../modules/cloudsql"
  name_prefix    = local.name_prefix
  region         = var.region
  vpc_id         = module.network.vpc_id
  env            = "staging"
  tier           = "db-custom-1-3840"
  psa_dependency = module.network.psa_connection
}

module "memorystore" {
  source         = "../../modules/memorystore"
  name_prefix    = local.name_prefix
  region         = var.region
  vpc_id         = module.network.vpc_id
  psa_range_name = module.network.psa_range_name
  env            = "staging"
  memory_gb      = 1
  depends_on     = [module.network]
}

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
