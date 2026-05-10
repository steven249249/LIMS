# Argo CD bootstrap

Run once per cluster.

```bash
# 1. Install Argo CD into its own namespace
kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd \
  --set server.service.type=ClusterIP \
  --set configs.params."server\.insecure"=true   # behind GKE Ingress; LB does TLS

# 2. Wait for the rollout
kubectl rollout status deploy/argocd-server -n argocd
kubectl rollout status statefulset/argocd-application-controller -n argocd

# 3. Initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d ; echo

# 4. Port-forward (or expose via Ingress later)
kubectl port-forward svc/argocd-server -n argocd 8080:80
# argocd login localhost:8080 --username admin --password <above>

# 5. Apply the AppProject + ApplicationSets
kubectl apply -f gitops/projects/lims.yaml
kubectl apply -f gitops/applicationsets/lims.yaml
kubectl apply -f gitops/applicationsets/observability.yaml
```

## External Secrets Operator (separate one-time install)

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace \
  --set installCRDs=true \
  --set serviceAccount.annotations."iam\.gke\.io/gcp-service-account"=\
"external-secrets@REPLACE-ME.iam.gserviceaccount.com"
```

Then create one `ClusterSecretStore` per project so the chart-level
ExternalSecret can reference it:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata: { name: gcpsm }
spec:
  provider:
    gcpsm:
      projectID: REPLACE-ME
      auth:
        workloadIdentity:
          clusterLocation: asia-east1
          clusterName: lims-prod-gke
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```
