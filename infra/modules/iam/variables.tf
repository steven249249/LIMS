variable "project_id"  { type = string }
variable "region"      { type = string, default = "asia-east1" }
variable "name_prefix" { type = string }
variable "namespace"   { type = string }   # K8s namespace the runtime SA binds into

variable "kubernetes_service_accounts" {
  type        = list(string)
  description = "K8s ServiceAccount names that can impersonate the runtime GSA."
  default     = ["lims-lims"] # default chart fullname (lims release × lims chart)
}

variable "enable_ci_builder" {
  type        = bool
  description = "Create the ci-builder SA + Workload Identity Federation pool. Set true in exactly ONE env (typically prod)."
  default     = false
}

variable "github_org"  { type = string, default = "REPLACE-ME" }
variable "github_repo" { type = string, default = "lims" }
