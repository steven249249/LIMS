# 02 · GCP 上線手冊 (UI + CLI step-by-step)

從零把 LIMS 部署到 GKE 的完整步驟。每一步都標明「在哪個 console 點什麼」、「跑什麼指令」、「成功應該看到什麼」。

> 🎯 **本手冊使用 Scenario B (demo) tier**,月費約 **$210**,$300 GCP free credit 撐 ~1.5 個月。所有功能保留 (frontend/backend/MySQL/Redis/Celery/observability/admin)。完整成本拆解 → [07-DEMO-COST-OPTIMIZATION.md](07-DEMO-COST-OPTIMIZATION.md)。

**預計時間:** 第一次跑大概 4-6 小時(包含 Cloud SQL 初始化 ~15 分鐘、ManagedCertificate 簽發 ~30 分鐘等待時間)。

**順序很重要 — 跨步驟有 dependency:**

```
1. GCP project + billing
2. APIs enable
3. State buckets
4. Secret Manager 種子值
5. Terraform apply (prod)
6. 把 Terraform output 填回 Helm values + GitHub repo
7. 把 IP 填到 DDNS A record
8. Argo CD bootstrap
9. 第一次 `argocd app sync lims-prod`
10. 等 ManagedCertificate 變綠
11. SmokeTest
```

---

## 步驟 0: 你需要的權限

- 一個有 **Billing Account Administrator** 跟 **Project Creator** 的 Google 帳號
- DDNS provider (`lims.ddns.net` 那邊) 的登入帳號
- 你 GitHub 的管理權限 (能改 `asddzxcc1856/LIMS` repo 的 Variables / Secrets,以及建立 Personal Access Token)

---

## 步驟 1: GCP project + Billing

### UI 操作

1. 開 https://console.cloud.google.com → 左上角專案下拉選單 → **新增專案**
2. 名稱:`LIMS Production`
3. **專案 ID** 自動產生(例如 `lims-prod-2026-xxxxxx`),**抄下來** — 接下來所有地方都會用到
4. 建好後,在搜尋欄打 **Billing** → **連結帳單帳戶**,選你的 billing account

### CLI 確認

```bash
gcloud config set project lims-prod-2026-xxxxxx       # 你的 project ID
gcloud projects describe $(gcloud config get-value project)
gcloud beta billing projects describe $(gcloud config get-value project)
```

第二行的 output 應該包含 `billingAccountName: billingAccounts/...`。沒有的話 Terraform 會在第一個 API 開啟時就失敗。

---

## 步驟 2: 開啟必要的 API

### CLI

```bash
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
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

要等 1-2 分鐘。確認:

```bash
gcloud services list --enabled --filter="name:(compute|container|sqladmin|redis|artifactregistry|secretmanager)"
```

要看到全部六個。

---

## 步驟 3: Terraform state buckets

每個環境一個 GCS bucket,開啟 versioning(state 寫壞時可以 rollback)。

### CLI

```bash
PROJECT=$(gcloud config get-value project)
for env in dev staging prod; do
  gcloud storage buckets create gs://lims-tfstate-$env \
    --project=$PROJECT --location=ASIA-EAST1 --uniform-bucket-level-access
  gcloud storage buckets update gs://lims-tfstate-$env --versioning
done
```

確認:

```bash
gsutil ls -L -b gs://lims-tfstate-prod | grep -E 'Versioning|Location'
# Versioning enabled:        True
# Location constraint:       ASIA-EAST1
```

---

## 步驟 4: Secret Manager 種子值 (prod 用)

每個環境的 secret 都有 `<env>-` prefix。Terraform 不種這些 — 它只 read,所以你必須先用 CLI 寫入。

### CLI

```bash
PROJECT=$(gcloud config get-value project)
ENV=prod    # 之後 dev / staging 重跑這個 block

# 4-1. Django SECRET_KEY — 隨機 50 字元
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | \
  gcloud secrets create lims-$ENV-django-secret-key --data-file=- --project=$PROJECT

# 4-2. DB password — 隨機 32 字元
python3 -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets create lims-$ENV-db-password --data-file=- --project=$PROJECT

# 4-3. 預設 admin 密碼 (你會用這個第一次登入 /admin/ 改其他帳號)
echo -n "ChangeMe_$(date +%Y)!Admin" | \
  gcloud secrets create lims-$ENV-lims-admin-password --data-file=- --project=$PROJECT

# 4-4. Sentry DSN — 不用 Sentry 就放空字串
echo -n "" | \
  gcloud secrets create lims-$ENV-sentry-dsn --data-file=- --project=$PROJECT
```

**Memorystore 的 redis-auth secret 不用手建 — Terraform memorystore 模組會在建好 Redis 之後自動把 AUTH string 塞進 Secret Manager。**

確認:

```bash
gcloud secrets list --filter="name:lims-prod-*"
# NAME                              CREATED              REPLICATION_POLICY
# lims-prod-django-secret-key       2026-05-10T07:50:00  automatic
# lims-prod-db-password             2026-05-10T07:50:01  automatic
# lims-prod-lims-admin-password     2026-05-10T07:50:02  automatic
# lims-prod-sentry-dsn              2026-05-10T07:50:03  automatic
```

> ⚠️ `lims-prod-lims-admin-password` 的初始值你 **必須** 在第一次部署完之後立刻換掉,因為 migration 會用這個 build 出超管帳號。建議流程:
> 1. 用初始密碼登入 `/django-admin/`
> 2. 進帳號管理把密碼重設成新的(這只改資料庫)
> 3. 把 Secret Manager 裡的也改掉(這只是讓重跑 `ensure_admin` 時知道新密碼)

---

## 步驟 5: 填寫 Terraform tfvars + apply

### 5-1. 填值

```bash
cd "/media/hcis-s15/ssd2/Lab project/infra/envs/prod"
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars,填三個 REPLACE-ME:
nano terraform.tfvars
```

```hcl
project_id  = "lims-prod-2026-xxxxxx"     # 你的 GCP project ID
github_org  = "asddzxcc1856"               # 你的 GitHub username (或 org)
github_repo = "LIMS"                       # repo 名 (大小寫要對 — GitHub URL 顯示是 LIMS)

authorized_networks = {
  "operator-home" = "REPLACE-ME/32"        # 你工作站的 public IP
}
```

要查你的 public IP:

```bash
curl -s https://api.ipify.org; echo
# 例如 203.0.113.42
# tfvars 寫 "203.0.113.42/32"
```

### 5-2. 安裝 Terraform (你應該還沒裝)

```bash
# 標準官方步驟,適用 Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
terraform version
```

### 5-3. terraform apply

```bash
cd "/media/hcis-s15/ssd2/Lab project/infra/envs/prod"

terraform init                      # 第一次跑會下載 google provider
terraform plan -out=plan.out         # 看會建哪些東西,大概 30-50 個 resource
terraform apply plan.out             # ⏰ 大概 15-20 分鐘
```

**過程中會發生:**

| 階段 | 約幾分鐘 | 在做什麼 |
|---|---|---|
| 0-1 min | Network (VPC, subnets, NAT, PSA range, ingress IP) | 快 |
| 1-3 min | IAM (runtime SA, ci-builder, WIF pool) | 快 |
| 3-15 min | GKE Autopilot cluster | **最久** |
| 5-18 min | Cloud SQL (private IP)+ Memorystore | 並行 |
| 15-20 min | 收尾 | 快 |

成功的 output 大概像這樣:

```
artifact_registry_path     = "asia-east1-docker.pkg.dev/lims-prod-2026-xxxxxx/lims"
ci_builder_email           = "ci-builder@lims-prod-2026-xxxxxx.iam.gserviceaccount.com"
cloudsql_connection_name   = "lims-prod-2026-xxxxxx:asia-east1:lims-prod-mysql"
cluster_name               = "lims-prod-gke"
ingress_static_ip_address  = "34.149.xxx.xxx"
ingress_static_ip_name     = "lims-prod-ingress-ip"
runtime_gsa_email          = "lims-prod-runtime@lims-prod-2026-xxxxxx.iam.gserviceaccount.com"
wif_provider_resource      = "projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
```

**抄下來,接下來會貼 4-5 個地方。**

### 5-4. 同樣的事在 dev / staging 重跑(可選)

如果你想要三個環境都建,把上面 5-1 ~ 5-3 在 `infra/envs/dev/` 和 `infra/envs/staging/` 各跑一次。每個環境會建獨立的 cluster + Cloud SQL,費用會三倍。

**不想花這個錢:** 只跑 prod,把 dev/staging 的 ApplicationSet element 從 `gitops/applicationsets/lims.yaml` 拿掉(或改 `autoSync: false` 永遠不 sync)。

---

## 步驟 6: 把 Terraform output 填回 chart + GitHub

這一步沒有 UI 操作,只是把上面抄的 output 貼到對應位置。

### 6-1. `helm/lims/values.yaml`

打開檔案,改:

```yaml
image:
  registry: asia-east1-docker.pkg.dev/lims-prod-2026-xxxxxx/lims   # ← Terraform 的 artifact_registry_path
```

### 6-2. `helm/lims/envs/prod.yaml`

```yaml
cloudSql:
  connectionName: lims-prod-2026-xxxxxx:asia-east1:lims-prod-mysql  # ← cloudsql_connection_name
serviceAccount:
  gsaEmail: lims-prod-runtime@lims-prod-2026-xxxxxx.iam.gserviceaccount.com  # ← runtime_gsa_email
```

### 6-3. GitHub repo Variables

到 https://github.com/asddzxcc1856/LIMS/settings/variables/actions,加四個 **Repository variables**:

| Name | Value |
|---|---|
| `GCP_PROJECT` | `lims-prod-2026-xxxxxx` |
| `AR_REGION` | `asia-east1` |
| `WIF_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GITOPS_REPO` | `asddzxcc1856/LIMS` (因為 GitOps 在 mono repo 裡) |

### 6-4. GitHub repo Secrets

到 https://github.com/asddzxcc1856/LIMS/settings/secrets/actions,加一個 **Repository secret**:

| Name | Value |
|---|---|
| `GITOPS_PAT` | 一個 fine-grained PAT,只給這個 repo `contents: write` 權限 |

**怎麼建 PAT:**

1. https://github.com/settings/personal-access-tokens/new
2. Token name: `lims-gitops-bumper`
3. Expiration: 90 天
4. Repository access → **Only select repositories** → `asddzxcc1856/LIMS`
5. Permissions → **Repository permissions** → `Contents: Read and write`
6. Generate → 複製 token,只會出現一次

### 6-5. `gitops/projects/lims.yaml`

把全部 `REPLACE-ME` 換成 `asddzxcc1856`。

### 6-6. Commit + push

```bash
cd "/media/hcis-s15/ssd2/Lab project"
git add helm/lims/values.yaml helm/lims/envs/prod.yaml gitops/projects/lims.yaml
git commit -m "Wire Terraform outputs into chart values + GitOps project"
git push
```

---

## 步驟 7: DDNS A record

`lims.ddns.net` 目前指向你家裡的 IP。要改成 GCLB 的靜態 IP。

### UI 操作 (取決於你用哪個 DDNS provider)

通常步驟是:
1. 登入 DDNS provider (no-ip / dynu / freedns / 等)
2. 找到 `lims.ddns.net` hostname
3. 把 **Hostname Type** / **Record Type** 從 `Dynamic` 改成 `Static A`
4. **Target IP** 填上 Terraform 的 `ingress_static_ip_address`(例如 `34.149.xxx.xxx`)
5. 儲存

### 確認

```bash
dig +short lims.ddns.net A
# 34.149.xxx.xxx       ← 應該等於 ingress_static_ip_address
```

DDNS 改動到 worldwide DNS 生效大概 5-15 分鐘。**這個必須先生效,ManagedCertificate 才簽得出來。**

---

## 步驟 8: Argo CD + ESO bootstrap

### 8-1. 拿到 cluster credentials

```bash
gcloud container clusters get-credentials lims-prod-gke \
  --region=asia-east1 --project=lims-prod-2026-xxxxxx
kubectl config current-context
# gke_lims-prod-2026-xxxxxx_asia-east1_lims-prod-gke
```

### 8-2. 裝 Argo CD

```bash
kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm install argocd argo/argo-cd -n argocd \
  --set server.service.type=ClusterIP \
  --set 'configs.params.server\.insecure=true' \
  --wait

# 拿初始 admin 密碼
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d ; echo
# 複製這串密碼 — 第一次登入用

# Port-forward 到本機開 UI
kubectl port-forward svc/argocd-server -n argocd 8080:80 &
# 開瀏覽器 http://localhost:8080,登入 admin / <上面那串>
```

### 8-3. 裝 External Secrets Operator + ClusterSecretStore

```bash
# 給 ESO 用的 GSA — 跟 Terraform 一起建會更乾淨,但這裡 manual 簡化版:
gcloud iam service-accounts create external-secrets \
  --project=lims-prod-2026-xxxxxx \
  --display-name="External Secrets Operator"

gcloud projects add-iam-policy-binding lims-prod-2026-xxxxxx \
  --member="serviceAccount:external-secrets@lims-prod-2026-xxxxxx.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud iam service-accounts add-iam-policy-binding \
  external-secrets@lims-prod-2026-xxxxxx.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:lims-prod-2026-xxxxxx.svc.id.goog[external-secrets/external-secrets]"

# 裝 ESO (Helm)
helm repo add external-secrets https://charts.external-secrets.io
helm repo update external-secrets
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace \
  --set installCRDs=true \
  --set "serviceAccount.annotations.iam\.gke\.io/gcp-service-account=external-secrets@lims-prod-2026-xxxxxx.iam.gserviceaccount.com" \
  --wait

# ClusterSecretStore
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata: { name: gcpsm }
spec:
  provider:
    gcpsm:
      projectID: lims-prod-2026-xxxxxx
      auth:
        workloadIdentity:
          clusterLocation: asia-east1
          clusterName: lims-prod-gke
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
EOF
```

驗證:

```bash
kubectl get clustersecretstore gcpsm -o jsonpath='{.status.conditions[*].status}'
# True
```

### 8-4. 套 AppProject + ApplicationSet

```bash
cd "/media/hcis-s15/ssd2/Lab project"
kubectl apply -f gitops/projects/lims.yaml
kubectl apply -f gitops/applicationsets/lims.yaml
kubectl apply -f gitops/applicationsets/observability.yaml      # 可選,先跳過減低複雜度
```

確認 ApplicationSet 生出 Application:

```bash
kubectl get applications -n argocd
# NAME           SYNC STATUS   HEALTH STATUS
# lims-dev       OutOfSync     Missing
# lims-staging   OutOfSync     Missing
# lims-prod      OutOfSync     Missing
```

> ⚠️ **lims-dev 跟 lims-staging 此時會自動 sync**(autoSync=true),如果你只 provision 了 prod 的 GCP infra 它們會 fail。最簡單:把 `gitops/applicationsets/lims.yaml` 裡 dev/staging 那兩行 element 刪掉再 apply,只留 prod。

---

## 步驟 9: 第一次 sync prod

prod 的 ApplicationSet 設成 `autoSync: false`,要在 Argo CD UI 手動點 Sync。

### UI 操作

1. Argo CD UI → Applications 頁 → 點 `lims-prod`
2. 右上角 **SYNC** 按鈕
3. 對話框 → **SYNCHRONIZE**
4. 看時間軸:
   - PreSync: `lims-lims-migrate` Job 跑 `python manage.py migrate --noinput` (~30 秒)
   - Sync: ConfigMap、Secret、Service、Deployment 一個一個建
   - Health: 等到 backend + frontend pod 都 Ready

### CLI

或你用 `argocd` CLI:

```bash
argocd login localhost:8080 --username admin --password <步驟 8-2 那串>
argocd app sync lims-prod --prune
argocd app wait lims-prod --health --timeout 600
```

---

## 步驟 10: 等 ManagedCertificate 變綠

### CLI

```bash
kubectl get managedcertificate -n lims-prod
# NAME             AGE   STATUS
# lims-lims-cert   5m    Active     ← 等到變這個
```

從 `Provisioning` 變 `Active` 通常要 15-60 分鐘。要看狀態細節:

```bash
kubectl describe managedcertificate -n lims-prod lims-lims-cert
# 看 Domain Status 那欄是不是 ACTIVE
```

**Provisioning 卡住的常見原因:**
- DDNS A record 還沒指到 GCLB IP → 用 `dig +short lims.ddns.net` 確認
- 域名 owner 沒開 ACME 規則(.ddns.net 通常 OK)

---

## 步驟 11: 全套煙霧測試

```bash
# 11-1. HTTPS 自動轉址
curl -I http://lims.ddns.net/
# HTTP/1.1 301 Moved Permanently
# Location: https://lims.ddns.net/

# 11-2. SPA 載入
curl -s https://lims.ddns.net/ | head -5
# <!DOCTYPE html> <html ...> ...

# 11-3. API health
curl -s https://lims.ddns.net/healthz
# {"status": "ok"}

curl -s https://lims.ddns.net/readyz
# {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}

# 11-4. 登入測試
curl -s -X POST https://lims.ddns.net/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<步驟 4 種的初始密碼>"}'
# {"access": "...", "refresh": "..."}
```

開瀏覽器到 `https://lims.ddns.net/`,用 admin 帳號登入,確認可以看到 dashboard。

---

## 你做完之後在 GCP / GitHub / DDNS 上會看到的東西

1. **GCP Compute Engine** → 一個 GKE Autopilot cluster (`lims-prod-gke`)
2. **GCP SQL** → 一個 MySQL 8 instance (`lims-prod-mysql`),private IP only
3. **GCP Memorystore** → 一個 Redis instance (`lims-prod-redis`),AUTH 已啟用
4. **GCP Artifact Registry** → 一個 Docker repo (`lims`),裡面會有 `backend` 跟 `frontend` 兩個 image
5. **GCP Networking → VPC** → `lims-prod-vpc`,一個 subnet + Cloud NAT + 一個全域靜態 IP
6. **GCP Networking → Load Balancing** → 一個 HTTPS LB,managed cert,backend pointing 到 GKE NEG
7. **GCP IAM** → `lims-prod-runtime` (pod 用)、`ci-builder` (CI 用)
8. **GCP Secret Manager** → 五個 secret(`lims-prod-django-secret-key`、`-db-password`、`-lims-admin-password`、`-sentry-dsn`、`-redis-auth`)
9. **GitHub Actions** → 每次 push 到 main 會 build + push image,然後改 `gitops/envs/dev/values.yaml`(prod 不會自動動)
10. **DDNS** → `lims.ddns.net` 指 GCP 的靜態 IP

---

## 出問題的時候

### Pod CrashLoopBackOff

```bash
kubectl describe pod -n lims-prod <pod-name>
kubectl logs -n lims-prod <pod-name> -c app --previous
```

### Migration Job 失敗

```bash
kubectl logs -n lims-prod -l app.kubernetes.io/component=migrate
```

最常見的是 Cloud SQL Auth Proxy 連不上 — 確認 `cloudsql.connectionName` 拼字對,以及 runtime SA 有 `roles/cloudsql.client`。

### 整個 namespace 重來

```bash
argocd app delete lims-prod --cascade
# 改完問題,重新 sync
argocd app create -f gitops/applicationsets/lims.yaml ... 或 kubectl apply
```

注意這 **不會** 刪 Cloud SQL 跟 Memorystore — 那些是 Terraform 管的,所以 dat 不會丟。

### Cloud SQL 想要還原到 N 分鐘前

```bash
# Cloud Console → SQL → lims-prod-mysql → Backups → Point-in-time recovery
# 選時間點 → 還原成 lims-prod-mysql-restored,然後切換 Helm connectionName
```

### 完全 destroy 重來

```bash
cd infra/envs/prod
# Cloud SQL deletion_protection 是 true,先關掉:
terraform apply -var='__force_disable_protection=true'   # 或手動編 main.tf
terraform destroy
```

只在最後手段用 — destroy 之後 IP / cluster name / 任何 reference 都會變。

---

## 跑完上面所有步驟後

回去看 [03-ACCOUNTS-AND-CREDENTIALS.md](03-ACCOUNTS-AND-CREDENTIALS.md) 處理使用者帳號,以及 [04-OPERATIONS-MANUAL.md](04-OPERATIONS-MANUAL.md) 知道日常怎麼維護。
