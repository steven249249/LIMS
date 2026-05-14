variable "project_id" { type = string }
variable "name_prefix" { type = string }
variable "region" {
  type    = string
  default = "asia-east1"
}
variable "vpc_id" { type = string }
variable "subnet_id" { type = string }
variable "env" { type = string } # dev | staging | prod

variable "master_cidr" {
  type    = string
  default = "172.16.0.0/28"
}

variable "authorized_networks" {
  type        = map(string)
  description = "Map of label -> CIDR allowed to reach the K8s API."
  default     = {}
  # Example:
  #   {
  #     "operator-home" = "203.0.113.0/32"
  #     "ci-egress-nat" = "198.51.100.0/32"
  #   }
}

variable "enable_managed_prometheus" {
  type        = bool
  description = "Use GKE Managed Prometheus (free 50M samples/mo). Cheaper than kube-prom-stack."
  default     = true
}

variable "binary_auth_mode" {
  type        = string
  description = "Binary Authorization eval mode. DISABLED for demo, PROJECT_SINGLETON_POLICY_ENFORCE for real prod."
  default     = "DISABLED"
}
