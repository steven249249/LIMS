variable "name_prefix"    { type = string }
variable "region"         { type = string, default = "asia-east1" }
variable "vpc_id"         { type = string }
variable "psa_range_name" { type = string }
variable "env"            { type = string }
variable "memory_gb"      { type = number, default = 1 }
