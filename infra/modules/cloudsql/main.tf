terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

resource "google_sql_database_instance" "mysql" {
  name             = "${var.name_prefix}-mysql"
  region           = var.region
  database_version = "MYSQL_8_0"

  # Hard-protect prod from accidental destroy. To delete, flip to false,
  # apply, then run terraform destroy.
  deletion_protection = var.env == "prod"

  settings {
    tier              = var.tier
    availability_type = var.env == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      binary_log_enabled             = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = var.env == "prod" ? 7 : 1
      backup_retention_settings {
        retained_backups = var.env == "prod" ? 30 : 7
      }
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.vpc_id
      enable_private_path_for_google_cloud_services = true
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }

    database_flags {
      name  = "cloudsql_iam_authentication"
      value = "on"
    }

    maintenance_window {
      day          = 7   # Sunday
      hour         = 18  # 18:00 UTC = 02:00 next day in Asia/Taipei
      update_track = "stable"
    }
  }

  depends_on = [var.psa_dependency]
}

resource "google_sql_database" "lims" {
  name      = var.database_name
  instance  = google_sql_database_instance.mysql.name
  charset   = "utf8mb4"
  collation = "utf8mb4_0900_ai_ci"
}

# Application user — the password rotates via Secret Manager + ESO; we
# read it from a SM secret so this resource doesn't bake plaintext into
# the Terraform state.
data "google_secret_manager_secret_version" "db_password" {
  secret = "${var.name_prefix}-db-password"
}

resource "google_sql_user" "lims" {
  name     = var.database_user
  instance = google_sql_database_instance.mysql.name
  password = data.google_secret_manager_secret_version.db_password.secret_data
}

output "connection_name" { value = google_sql_database_instance.mysql.connection_name }
output "private_ip"      { value = google_sql_database_instance.mysql.private_ip_address }
output "instance_name"   { value = google_sql_database_instance.mysql.name }
