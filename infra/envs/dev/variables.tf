variable "project_id"          { type = string }
variable "region"              { type = string, default = "asia-east1" }
variable "authorized_networks" { type = map(string), default = {} }
