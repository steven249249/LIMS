variable "name_prefix" { type = string }
variable "region"      { type = string, default = "asia-east1" }
variable "vpc_id"      { type = string }
variable "env"         { type = string }   # dev | staging | prod

variable "tier" {
  type        = string
  description = <<-EOT
    Cloud SQL machine tier.
      dev:     db-f1-micro            (~$10/mo, ZONAL)
      staging: db-custom-1-3840       (~$50/mo, ZONAL)
      prod:    db-custom-2-7680       (~$200/mo, REGIONAL/HA)
  EOT
  default     = "db-f1-micro"
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
