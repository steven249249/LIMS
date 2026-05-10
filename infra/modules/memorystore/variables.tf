variable "name_prefix"    { type = string }
variable "region"         { type = string, default = "asia-east1" }
variable "vpc_id"         { type = string }
variable "psa_range_name" { type = string }
variable "env"            { type = string }
variable "memory_gb"      { type = number, default = 1 }
variable "tier" {
  type        = string
  description = "BASIC (single-node, ~$40/mo per GB) or STANDARD_HA (replica, ~2x cost)."
  default     = "BASIC"
  validation {
    condition     = contains(["BASIC", "STANDARD_HA"], var.tier)
    error_message = "tier must be BASIC or STANDARD_HA."
  }
}
