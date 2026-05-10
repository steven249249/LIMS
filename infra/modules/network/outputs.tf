output "vpc_id"        { value = google_compute_network.vpc.id }
output "vpc_name"      { value = google_compute_network.vpc.name }
output "gke_subnet_id" { value = google_compute_subnetwork.gke.id }

# Used by Cloud SQL + Memorystore modules so Terraform sequences the
# `depends_on` correctly — they can only attach after the PSA peering exists.
output "psa_connection" { value = google_service_networking_connection.psa }
output "psa_range_name" { value = google_compute_global_address.psa_range.name }
output "psa_cidr"       { value = "${google_compute_global_address.psa_range.address}/${google_compute_global_address.psa_range.prefix_length}" }

# For the Helm chart's ingress.staticIp value + the DNS A record.
output "ingress_static_ip_name"    { value = google_compute_global_address.ingress_ip.name }
output "ingress_static_ip_address" { value = google_compute_global_address.ingress_ip.address }
