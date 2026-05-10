terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

# One Artifact Registry repo for the whole project — backend and frontend
# images both live here, distinguished by repository name (lims/backend,
# lims/frontend). Immutable tags is the critical setting: prevents
# `latest` overwrites and reasserts that the SHA-tagged image you reviewed
# is the SHA-tagged image that runs.
resource "google_artifact_registry_repository" "lims" {
  location      = var.region
  repository_id = "lims"
  format        = "DOCKER"

  docker_config {
    immutable_tags = true
  }

  cleanup_policies {
    id     = "keep-recent-tagged"
    action = "KEEP"
    most_recent_versions {
      keep_count = 50
    }
  }
  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }
}

output "repository_path" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.lims.repository_id}"
}
