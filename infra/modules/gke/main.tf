terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

# GKE Autopilot — Google manages the node pool, security posture is set by
# Google's defaults (which already enforce most of what we'd otherwise have
# to configure manually: shielded nodes, workload identity, RBAC, etc.).
resource "google_container_cluster" "this" {
  name             = "${var.name_prefix}-gke"
  location         = var.region
  enable_autopilot = true

  network    = var.vpc_id
  subnetwork = var.subnet_id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Private nodes — workers have only RFC1918 IPs. Master is reachable
  # only from the listed CIDRs (operator workstation + GitHub runners
  # via NAT egress IP if you want kubectl from CI).
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_cidr
  }

  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.authorized_networks
      content {
        cidr_block   = cidr_blocks.value
        display_name = cidr_blocks.key
      }
    }
  }

  # Workload Identity binds K8s ServiceAccounts to GCP service accounts so
  # pods authenticate to GCP APIs without long-lived keys.
  workload_identity_config { workload_pool = "${var.project_id}.svc.id.goog" }

  release_channel { channel = "REGULAR" }

  # Cloud Logging is on (system + workloads). For demo we also enable
  # Managed Prometheus so /metrics scraping works without running a
  # self-hosted Prometheus + Loki + Tempo stack (saves ~$30-50/mo on
  # observability pods). Cloud Trace + Cloud Logging + Managed Prometheus
  # together replace the kube-prometheus-stack / Loki / Tempo trio.
  logging_config { enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"] }
  monitoring_config {
    enable_components  = ["SYSTEM_COMPONENTS"]
    managed_prometheus { enabled = var.enable_managed_prometheus }
  }

  # Binary Authorization adds complexity without saving money. Leave OFF
  # for the demo; flip to ENFORCE if/when this becomes a real production
  # workload.
  binary_authorization {
    evaluation_mode = var.binary_auth_mode
  }

  # Block accidental destroy in prod. Toggle off, then `terraform apply`
  # again before you can `terraform destroy` in an emergency.
  deletion_protection = var.env == "prod"
}

output "cluster_name"     { value = google_container_cluster.this.name }
output "cluster_endpoint" { value = google_container_cluster.this.endpoint, sensitive = true }
output "cluster_ca_cert"  { value = google_container_cluster.this.master_auth[0].cluster_ca_certificate, sensitive = true }
