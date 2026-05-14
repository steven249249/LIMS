# Copy to terraform.tfvars and fill in.

project_id  = "flawless-psyche-495420-h5"
github_org  = "asddzxcc1856"
github_repo = "LIMS"

# Operator workstation IP(s). Only these can reach the GKE API server.
authorized_networks = {
  "operator-home" = "23.97.62.137/32"
}
