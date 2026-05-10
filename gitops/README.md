# LIMS GitOps repo

Argo CD watches **this directory tree** (whether it lives in this same
repo or a separated `lims-gitops` repo) and reconciles the in-cluster
state to match.

## Layout

```
gitops/
├── README.md
├── bootstrap/
│   ├── argocd.md                  one-time install steps
│   └── root-app.yaml              "app of apps" entry point
├── projects/
│   └── lims.yaml                  AppProject (RBAC scope)
├── applicationsets/
│   ├── lims.yaml                  3 envs (dev, staging, prod) of the LIMS chart
│   └── observability.yaml         kube-prom-stack, Loki, Tempo, OTel Collector
└── envs/
    ├── dev/values.yaml            CI bumps image.tag here on every dev push
    ├── staging/values.yaml
    └── prod/values.yaml
```

## Sync policy summary

| Env | autoSync | selfHeal | prune | Notes |
|---|---|---|---|---|
| dev | yes | yes | yes | CI tag bumps deploy automatically |
| staging | yes | yes | yes | manual PR promotes dev tag → staging |
| prod | **no** | no | no | manual `argocd app sync lims-prod` after a green staging soak |

## Bootstrap order

```bash
# 1. Apply AppProject (RBAC scope)
kubectl apply -f projects/lims.yaml

# 2. Apply ApplicationSets — generates one Argo CD Application per env
kubectl apply -f applicationsets/lims.yaml
kubectl apply -f applicationsets/observability.yaml
```

## Splitting into a separate repo (optional, recommended for prod)

The same files relocate verbatim. Update `repoURL` in each
ApplicationSet to point at the new repo, and grant Argo CD's
`argocd-application-controller` SA read access via a deploy key /
GitHub App / PAT.
