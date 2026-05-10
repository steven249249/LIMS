# LIMS Helm chart

Renders the LIMS stack (backend Deployment + Service, frontend Deployment +
Service, optional Celery worker, migration Job, GKE Ingress + ManagedCertificate +
BackendConfig, HPA, PDB, NetworkPolicy, PodMonitor, ExternalSecret) for one
environment.

## Render & install

```bash
# Smoke-render with dev values
helm template lims helm/lims/ -f helm/lims/envs/dev.yaml

# Install into a kind cluster
helm install lims helm/lims/ \
  -f helm/lims/envs/dev.yaml \
  --set image.tag=$(git rev-parse --short=12 HEAD) \
  --create-namespace \
  --namespace lims-dev
```

`image.tag` has no default — CI bumps it in `lims-gitops/envs/<env>/values.yaml`
on every successful build, never the literal `latest`.

## What lives where

| File | Purpose |
|---|---|
| `Chart.yaml` | Helm chart metadata. |
| `values.yaml` | Conservative production-leaning defaults. |
| `envs/{dev,staging,prod}.yaml` | Per-environment overrides. |
| `templates/_helpers.tpl` | Common name/label helpers + securityContext blocks. |
| `templates/serviceaccount.yaml` | KSA annotated for Workload Identity. |
| `templates/configmap.yaml` | Non-sensitive config (DB host, Redis URL, env vars). |
| `templates/externalsecret.yaml` | Pulls secrets from GCP Secret Manager via ESO. |
| `templates/deployment-backend.yaml` | Django + gunicorn + Cloud SQL Auth Proxy sidecar. |
| `templates/deployment-frontend.yaml` | nginx serving the built SPA on :8080. |
| `templates/deployment-celery.yaml` | Celery worker (off by default). |
| `templates/services.yaml` | ClusterIP Services for backend + frontend. |
| `templates/ingress.yaml` | GKE Ingress, ManagedCertificate, BackendConfig, FrontendConfig. |
| `templates/hpa-pdb.yaml` | HorizontalPodAutoscaler + PodDisruptionBudget. |
| `templates/job-migrate.yaml` | Argo CD `PreSync` migration Job. |
| `templates/networkpolicy.yaml` | Default-deny + LB allow + Prometheus allow + egress allow. |
| `templates/podmonitor.yaml` | Prometheus Operator scrape target for backend `/metrics`. |

## What's intentionally NOT in the chart

* Cloud SQL instance, Memorystore instance, Artifact Registry repo, IAM
  service accounts, Workload Identity bindings — those live in Terraform
  (`lims-infra` repo). The chart only references the connection name +
  GSA email.
* Cloud Armor security policies, DNS records — Terraform.
* The observability stack (kube-prometheus-stack, Loki, Tempo, OTel
  Collector, Grafana) — separate Argo CD Application against the upstream
  charts in the `observability` namespace.
