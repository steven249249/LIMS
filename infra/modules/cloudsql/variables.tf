variable "name_prefix" { type = string }
variable "region"      { type = string, default = "asia-east1" }
variable "vpc_id"      { type = string }
variable "env"         { type = string }   # dev | staging | prod

variable "tier" {
  type        = string
  description = <<-EOT
    Cloud SQL machine tier.
      Cheapest demo path:  db-custom-1-3840   (~$50/mo, ZONAL)
      Real prod (HA):      db-custom-2-7680   (~$200/mo, REGIONAL)
  EOT
  default     = "db-custom-1-3840"
}

variable "availability_type" {
  type        = string
  description = "ZONAL (cheaper, single-AZ) or REGIONAL (HA, ~2x cost)."
  default     = "ZONAL"
  validation {
    condition     = contains(["ZONAL", "REGIONAL"], var.availability_type)
    error_message = "availability_type must be ZONAL or REGIONAL."
  }
}

variable "deletion_protection" {
  type        = bool
  description = "If true, `terraform destroy` is blocked until you flip this off + apply."
  default     = false
}

variable "database_name" {
  type    = string
  default = "lab_booking"
}

variable "database_user" {
  type    = string
  default = "lims_app"
}

# Pass in module.network.psa_connection so Cloud SQL waits for the peering
# to exist before it tries to use a private IP.
variable "psa_dependency" {
  type    = any
  default = null
}
