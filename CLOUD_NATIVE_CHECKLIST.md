# Cloud-Native Bring-Up Checklist

Use this as the single source of truth for what to fill in when the real
GCP project is ready. Search the repo for `REPLACE-ME` to find every spot
that needs a real value.

> 🎯 **Repo defaults are Scenario B (demo, ~$210/mo).** Cloud SQL =
> `db-custom-1-3840` ZONAL, Memorystore = BASIC 1 GB, GKE = Managed
> Prometheus (no self-hosted Prom stack). $300 free credit covers ~1.5
> months. To convert to real production tier, see
> [docs/07-DEMO-COST-OPTIMIZATION.md §F](docs/07-DEMO-COST-OPTIMIZATION.md).

## 0. Decide the names

| Variable | Suggested value | Where to set |
|---|---|---|
| GCP project ID | e.g. `lims-prod-2026` | `infra/envs/*/terraform.tfvars` (`project_id`) |
| GCP region | `asia-east1` | already the default |
| GitHub org/owner | e.g. `asddzxcc1856` | `infra/envs/prod/terraform.tfvars` (`github_org`), `gitops/projects/lims.yaml` |
| Cluster names | `lims-{dev,staging,prod}-gke` | derived in TF; nothing to type |
| Prod DNS | `lims.ddns.net` (already wired) | already in `helm/lims/envs/prod.yaml` |
| Dev DNS | TODO – e.g. `lims-dev.ddns.net` (register a separate DDNS hostname) | `helm/lims/envs/dev.yaml` |
| Staging DNS | TODO – e.g. `lims-staging.ddns.net` | `helm/lims/envs/staging.yaml` |

## 1. Bootstrap (one-off, manual)

```bash
gcloud projects create REPLACE-ME --name="LIMS"
gcloud beta billing projects link REPLACE-ME --billing-account=REPLACE-ME
gcloud services enable compute.googleapis.com container.googleapis.com \
  servicenetworking.googleapis.com sqladmin.googleapis.com redis.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com --project=REPLACE-ME

for env in dev staging prod; do
  gcloud storage buckets create gs://lims-tfstate-$env \
    --project=REPLACE-ME --location=ASIA-EAST1 --uniform-bucket-level-access
  gcloud storage buckets update gs://lims-tfstate-$env --versioning
done
```

## 2. Provision infra (per env)

```bash
cd infra/envs/prod
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars                    # fill in REPLACE-ME

terraform init
terraform plan -out=plan.out
terraform apply plan.out
```

After apply, copy outputs into Helm values:

```
$ terraform output
artifact_registry_path     = "asia-east1-docker.pkg.dev/<proj>/lims"
ci_builder_email           = "ci-builder@<proj>.iam.gserviceaccount.com"
cloudsql_connection_name   = "<proj>:asia-east1:lims-prod-mysql"
ingress_static_ip_address  = "34.x.x.x"
ingress_static_ip_name     = "lims-prod-ingress-ip"
runtime_gsa_email          = "lims-prod-runtime@<proj>.iam.gserviceaccount.com"
wif_provider_resource      = "projects/.../providers/github-provider"
```

| Terraform output | Where to paste |
|---|---|
| `artifact_registry_path` | `helm/lims/values.yaml` → `image.registry` |
| `cloudsql_connection_name` | `helm/lims/envs/<env>.yaml` → `cloudSql.connectionName` |
| `runtime_gsa_email` | `helm/lims/envs/<env>.yaml` → `serviceAccount.gsaEmail` |
| `ingress_static_ip_name` | `helm/lims/envs/<env>.yaml` → `ingress.staticIp` (already pre-set) |
| `ingress_static_ip_address` | DDNS A record for `lims.ddns.net` |
| `wif_provider_resource` | GitHub repo variable `WIF_PROVIDER` |
| (project ID) | GitHub repo variable `GCP_PROJECT` |
| (region) | GitHub repo variable `AR_REGION` |

## 3. Seed Secret Manager

```bash
ENV=prod   # or dev / staging
for k in django-secret-key db-password lims-admin-password sentry-dsn \
         redis-auth; do
  echo "$RANDOM_VALUE_FOR_$k" | gcloud secrets create lims-$ENV-$k \
    --data-file=- --project=REPLACE-ME
done
```

Use long random strings for `django-secret-key`. The `redis-auth` secret
is auto-created by the Memorystore Terraform module — only the four
others need manual seeding.

## 4. Bootstrap Argo CD on each cluster

```bash
gcloud container clusters get-credentials lims-prod-gke \
  --region=asia-east1 --project=REPLACE-ME

# follow gitops/bootstrap/argocd.md
helm install argocd argo/argo-cd -n argocd --create-namespace ...
helm install external-secrets external-secrets/external-secrets ...
kubectl apply -f gitops/projects/lims.yaml
kubectl apply -f gitops/applicationsets/lims.yaml
kubectl apply -f gitops/applicationsets/observability.yaml
```

## 5. Wire CI

GitHub repo → Settings → Variables and Secrets:

- `vars.GCP_PROJECT` = your project ID
- `vars.AR_REGION` = `asia-east1`
- `vars.WIF_PROVIDER` = `projects/<num>/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- `vars.GITOPS_REPO` = `<owner>/lims` (or `<owner>/lims-gitops`)
- `secrets.GITOPS_PAT` = a fine-grained PAT with `contents:write` on the GitOps repo

The `cd.yml` workflow then runs on every push to main and bumps
`gitops/envs/dev/values.yaml`.

## 6. DDNS A record

Once `terraform output ingress_static_ip_address` returns the prod IP,
update lims.ddns.net's A record to that IP. From that point on the GKE
ManagedCertificate will issue a Google-managed cert for the domain.

## 7. Local validation BEFORE GCP cutover

```bash
make kind-up kind-deps kind-build kind-load kind-deploy kind-status
# point browser at http://localhost:8080 (kind-config maps it)
make kind-test       # hits /healthz + /readyz
make kind-down
```
