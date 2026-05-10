terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

# ── Runtime service account: pods authenticate as this via Workload Identity.
resource "google_service_account" "runtime" {
  account_id   = "${var.name_prefix}-runtime"
  display_name = "${var.name_prefix} runtime SA"
  description  = "Used by application pods (backend, celery, migration Job) via Workload Identity."
}

# Cloud SQL Auth Proxy needs Cloud SQL Client to connect.
resource "google_project_iam_member" "runtime_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Read application secrets from Secret Manager. Restricted to secrets
# whose name starts with `<name_prefix>-` so dev pods can't read prod
# secrets if cluster boundaries are ever crossed.
resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"

  condition {
    title       = "${var.name_prefix}-secret-prefix-only"
    description = "Only secrets named ${var.name_prefix}-* are readable."
    expression  = "resource.name.startsWith('projects/${var.project_id}/secrets/${var.name_prefix}-')"
  }
}

# Workload Identity binding: the K8s SA `<namespace>/<ksa>` impersonates
# this GSA. The `<ksa>` is whatever the Helm chart names it
# (lims-<release>) so we reference both possibilities.
resource "google_service_account_iam_member" "runtime_wi" {
  for_each           = toset(var.kubernetes_service_accounts)
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.namespace}/${each.value}]"
}

# ── CI builder service account (created once at the project level — only
# the prod env module instantiates this. Dev/staging modules pass the
# `enable_ci_builder = false` flag.)
resource "google_service_account" "ci_builder" {
  count        = var.enable_ci_builder ? 1 : 0
  account_id   = "ci-builder"
  display_name = "GitHub Actions CI builder"
}

resource "google_artifact_registry_repository_iam_member" "ci_writer" {
  count      = var.enable_ci_builder ? 1 : 0
  project    = var.project_id
  location   = var.region
  repository = "lims"
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci_builder[0].email}"
}

# Workload Identity Federation pool for GitHub OIDC. Created once.
resource "google_iam_workload_identity_pool" "gh" {
  count                     = var.enable_ci_builder ? 1 : 0
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "gh" {
  count                              = var.enable_ci_builder ? 1 : 0
  workload_identity_pool_id          = google_iam_workload_identity_pool.gh[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "attribute.repository == \"${var.github_org}/${var.github_repo}\""
}

resource "google_service_account_iam_member" "ci_wif_binding" {
  count              = var.enable_ci_builder ? 1 : 0
  service_account_id = google_service_account.ci_builder[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.gh[0].name}/attribute.repository/${var.github_org}/${var.github_repo}"
}

output "runtime_gsa_email" { value = google_service_account.runtime.email }

output "ci_builder_email" {
  value       = try(google_service_account.ci_builder[0].email, null)
  description = "Empty unless enable_ci_builder = true."
}

output "wif_provider_resource" {
  value       = try(google_iam_workload_identity_pool_provider.gh[0].name, null)
  description = "Pass to google-github-actions/auth `workload_identity_provider`."
}
