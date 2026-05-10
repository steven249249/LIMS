# LIMS infrastructure (Terraform)

Provisions the GCP foundation for the LIMS GKE deployment:

- VPC + subnets + Cloud NAT + Private Service Access range
- GKE Autopilot cluster (regional, private nodes)
- Cloud SQL for MySQL 8 (private IP, automated backups)
- Memorystore Redis (private IP, AUTH enabled)
- Artifact Registry Docker repo (immutable tags)
- Reserved global static IP for the Ingress
- IAM service accounts + Workload Identity bindings
  (one runtime SA per env + one CI builder SA + one Terraform SA)
- Workload Identity Federation for GitHub Actions OIDC

## Layout

```
infra/
├── README.md
├── modules/
│   ├── network/
│   ├── gke/
│   ├── cloudsql/
│   ├── memorystore/
│   ├── artifact-registry/
│   └── iam/
└── envs/
    ├── dev/
    ├── staging/
    └── prod/
```

Every `envs/*/terraform.tfvars.example` file marks unfilled placeholders
with `REPLACE-ME`. Copy to `terraform.tfvars` and fill in real values
before running `terraform plan`.

## Bootstrap order (do this once, manually)

Terraform needs a state bucket to live in **before** it can manage
anything. Bootstrap order:

```bash
# 1. GCP project + billing
gcloud projects create REPLACE-ME --name="LIMS" --set-as-default
gcloud beta billing projects link REPLACE-ME --billing-account=REPLACE-ME

# 2. Enable APIs that Terraform needs to see itself
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  servicenetworking.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project=REPLACE-ME

# 3. State buckets (one per env, versioned)
for env in dev staging prod; do
  gcloud storage buckets create gs://lims-tfstate-$env \
    --project=REPLACE-ME --location=ASIA-EAST1 --uniform-bucket-level-access
  gcloud storage buckets update  gs://lims-tfstate-$env --versioning
done

# 4. A user with Owner role to run TF the first time. After the IAM module
#    creates terraform-<env>@... service accounts, switch to those via WIF.
```

## Per-environment apply

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars   # then fill in REPLACE-ME values
terraform init
terraform plan -out=plan.out
terraform apply plan.out
```

Outputs you'll need to wire into the Helm chart values
(`helm/lims/envs/<env>.yaml`):

| Terraform output | Helm key |
|---|---|
| `cloudsql_connection_name` | `cloudSql.connectionName` |
| `redis_url` | `redis.url` |
| `artifact_registry_path` | `image.registry` (in `helm/lims/values.yaml`) |
| `runtime_gsa_email` | `serviceAccount.gsaEmail` |
| `ingress_static_ip_name` | `ingress.staticIp` |
| `ingress_static_ip_address` | (for the DDNS A record) |
