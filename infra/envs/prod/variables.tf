variable "project_id" {
  type        = string
  description = "GCP project ID. REPLACE-ME."
}

variable "region" {
  type    = string
  default = "asia-east1"
}

variable "github_org" {
  type        = string
  description = "GitHub org/user that owns the lims repo. REPLACE-ME."
}

variable "github_repo" {
  type    = string
  default = "lims"
}

variable "authorized_networks" {
  type        = map(string)
  description = "CIDRs allowed to reach the K8s API directly. Operator IPs only."
  default     = {}
  # Example:
  #   authorized_networks = {
  #     "operator-home" = "203.0.113.10/32"
  #   }
}
