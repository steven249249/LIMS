variable "name_prefix" {
  type        = string
  description = "e.g. lims-dev / lims-staging / lims-prod. Names every resource."
}

variable "region" {
  type    = string
  default = "asia-east1"
}

variable "gke_subnet_cidr" {
  type        = string
  description = "Primary GKE subnet for nodes. /20 is plenty."
  default     = "10.10.0.0/20"
}

variable "pods_cidr" {
  type        = string
  description = "Secondary range for Pod IPs. Must not overlap with services_cidr."
  default     = "10.20.0.0/16"
}

variable "services_cidr" {
  type        = string
  description = "Secondary range for ClusterIP Service IPs."
  default     = "10.30.0.0/20"
}
