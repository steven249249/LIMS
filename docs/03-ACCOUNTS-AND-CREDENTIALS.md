# 03 · 帳號 / 密碼 / 角色清單

整個系統會用到的帳號分四層:
- **GCP IAM** — 你跟 CI 用來操作 cloud
- **Kubernetes** — 集群層級的權限
- **LIMS 內部使用者** — 端使用者跟 lab manager 登入 SPA 用
- **第三方** — Sentry / DDNS / GitHub

下面每一層都列出:有哪些帳號、哪裡可以改、初始密碼怎麼來、誰應該用。

---

## A. GCP IAM (cloud 層)

### A-1. Service Accounts (機器用)

| SA email | 用途 | 誰會用 | 角色 |
|---|---|---|---|
| `lims-prod-runtime@<proj>.iam.gserviceaccount.com` | App pod 跟 GCP API 對話 | 透過 Workload Identity 由 K8s pod 借用,**人不該用** | `roles/cloudsql.client`、`roles/secretmanager.secretAccessor` (限 `lims-prod-*`) |
| `lims-dev-runtime@...`、`lims-staging-runtime@...` | 同上,各 env 各一個 | dev/staging 的 pod | 同上但限自己 prefix |
| `ci-builder@<proj>.iam.gserviceaccount.com` | GitHub Actions build & push | 透過 Workload Identity Federation 由 GitHub OIDC 借用 | `roles/artifactregistry.writer` |
| `external-secrets@<proj>.iam.gserviceaccount.com` | ESO 從 Secret Manager 拉 secret | ESO controller pod | `roles/secretmanager.secretAccessor` |
| `terraform-prod@<proj>.iam.gserviceaccount.com` | Terraform 跑 IaC (還沒建,可選) | CI 或 你 sudo 跑 TF | `roles/owner` 或細拆 |

### A-2. 真人帳號

| 帳號類型 | 角色 | 在哪管理 |
|---|---|---|
| Project Owner | 最大權限 | Cloud Console → IAM & Admin → IAM |
| Editor | 改 cluster / DB / etc. | 同上 |
| `roles/container.viewer` | 只讀 GKE | 同上 |
| `roles/cloudsql.viewer` | 只讀 Cloud SQL | 同上 |

**建議:** 你個人帳號保留 Owner;之後給隊友的話用 `roles/container.developer` + `roles/cloudsql.client`,不要直接給 Owner。

---

## B. Kubernetes 層

### B-1. ServiceAccounts (跑在 cluster 內)

| KSA | namespace | 綁定的 GSA | 用來做什麼 |
|---|---|---|---|
| `lims-lims` | `lims-prod` | `lims-prod-runtime@...` | 所有 LIMS pod (backend, frontend, celery, migrate) |
| `external-secrets` | `external-secrets` | `external-secrets@...` | ESO controller |
| `argocd-server`、`argocd-application-controller` | `argocd` | (沒綁,只跟 API server 對話) | Argo CD 自己 |

### B-2. Argo CD 的真人帳號

裝完之後預設只有一個 `admin` 帳號:

| 用法 | 怎麼拿初始密碼 |
|---|---|
| 第一次登入 | `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' \| base64 -d` |

**第一次登入完立刻換掉,然後刪掉 initial secret:**

```bash
argocd login localhost:8080 --username admin --password <initial>
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

**之後給隊友帳號:** 編 `argocd-cm` ConfigMap 加 `accounts.<username>: apiKey, login`,再 `argocd account update-password --account <username>`。

### B-3. AppProject roles (角色 RBAC)

`gitops/projects/lims.yaml` 裡定義了兩個角色:

| Role | 能做什麼 | 應該給誰 |
|---|---|---|
| `read-only` | 看 Application 狀態 | 整個團隊 |
| `deployer` | trigger sync (但不能刪 Application) | 主要工程師 |

把 GitHub group 名填到 `gitops/projects/lims.yaml` 的 `groups:` 區塊,搭配 Argo CD 的 SSO (Dex/OIDC) 整合 — 但這要另外設,目前這個 file 把 group 名標 `REPLACE-ME`。

---

## C. LIMS 內部使用者(SPA 登入)

LIMS 的 user system 有四個 role,定義在 `backend/users/models.py:User.Role`:

| Role | 看得到什麼 | 能做什麼 |
|---|---|---|
| `regular_employee` (廠區使用者) | 自己送的訂單 | 送樣 (`/orders/create`)、看自己訂單列表 |
| `lab_member` (實驗室成員) | 指派給自己的 stage | 完成 stage、看實驗室任務 |
| `lab_manager` (實驗室主管) | 自己實驗室的訂單 + stage + 機台 | 排程、指派機台、駁回 |
| `superuser` | 全部 | 上述全部 + admin console (`/admin/*`) |

### C-1. 第一次部署時自動建立的帳號 (demo seed)

**只在 `SEED_DEMO_DATA=True` 時才會跑** (本地 kind 預設 True;dev/staging/prod 預設 False)。

帳號清單來自 `backend/users/migrations/0003_create_demo_org.py`:

| Username | Role | 部門 |
|---|---|---|
| `Lab_Mgr_Photo` | lab_manager | Photolithography Lab |
| `Lab_Mem_Photo_001` | lab_member | Photolithography Lab |
| `Lab_Mgr_Process` | lab_manager | Thin Film & Etch Lab |
| `Lab_Mem_Process_001` | lab_member | Thin Film & Etch Lab |
| `Lab_Mgr_QC` | lab_manager | Metrology & Inspection Lab |
| `Lab_Mem_QC_001` | lab_member | Metrology & Inspection Lab |
| `testuser` | regular_employee | Photolithography Lab |

**統一密碼:** `Lims@2026!Init` (env var `LIMS_DEMO_PASSWORD` 可以蓋過)。

> ⚠️ 在 prod (`SEED_DEMO_DATA=False`) 你不會有這些帳號,所以第一次登入只能用下面 C-2 的 admin。

### C-2. Superuser 帳號 (production 必有)

來自 `backend/users/migrations/0002_create_default_admin.py`:

| Username | Role | 初始密碼 |
|---|---|---|
| `admin` | superuser | 來自環境變數 `LIMS_ADMIN_PASSWORD`,在 GCP 從 Secret Manager `lims-prod-lims-admin-password` 拉 |

**強制流程 (上線後第一天必做):**

1. 用初始密碼登入 `https://lims.ddns.net/django-admin/`
2. 進 `Users` → `admin` → 改密碼
3. 也建議改 username 從 `admin` 變成你自己的(改 `is_superuser=True` 然後刪掉 admin)
4. 改完後同步把 GCP Secret Manager 裡的 `lims-prod-lims-admin-password` 也更新成新密碼(這個 secret 之後只會被 `manage.py ensure_admin` 重跑時用,所以保持一致比較好除錯)

```bash
echo -n "<新密碼>" | gcloud secrets versions add lims-prod-lims-admin-password \
  --data-file=- --project=lims-prod-2026-xxxxxx
```

### C-3. 建後續使用者的方式

#### 從 admin console UI

`https://lims.ddns.net/admin` (注意是 `/admin` 不是 `/django-admin`,這是我們自己的 admin SPA) → Users → 點 `+ New`。

#### 從 admin console 批次建立

`/admin/users/` 頁面有一個 **Bulk Create** 按鈕:

- 選 role (`regular_employee` / `lab_member` / `lab_manager`)
- 選 department
- 選數量 N
- 系統自動產 username:
  - `regular_employee` → `Emp_001`、`Emp_002`...
  - `lab_member` → `LabMem_<dept>_001`...
  - `lab_manager` → `LabMgr_<dept>_001`...
- 全部用同一個初始密碼:`Lims@2026!Init` (env var `LIMS_BULK_PASSWORD` 可以蓋過)

#### 直接打 API

```bash
curl -X POST https://lims.ddns.net/api/admin/users/ \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@lims","password":"InitPass!","role":"regular_employee","department":"<dept-uuid>"}'
```

---

## D. 第三方服務帳號

### D-1. GitHub

| 用法 | 設在哪 |
|---|---|
| Repo admin (你個人帳號) | github.com 個人 |
| `GITOPS_PAT` secret | github.com/asddzxcc1856/LIMS/settings/secrets — fine-grained PAT,90 天到期前要 rotate |
| `WIF_PROVIDER` variable | 同上 settings/variables |
| Workload Identity Federation pool | GCP IAM 自己 (Terraform 管) |

### D-2. DDNS provider (`lims.ddns.net`)

- 原本指你家裡的 IP,改成 GCP static IP 之後通常不會再動
- 帳號保管好;如果 hostname 失效會整個服務沒辦法存取
- **建議:** 開帳號的 2FA

### D-3. Sentry (可選)

- 沒申請 Sentry 就把 `lims-prod-sentry-dsn` 放空字串(`backend/backend/settings.py:262-276` 會 silently 跳過 init)
- 申請了之後:在 Sentry 建一個 project,複製 DSN,塞到 Secret Manager

---

## E. 密碼輪替政策建議

| 對象 | 多久換一次 | 怎麼換 |
|---|---|---|
| `admin` 帳號 | 90 天 | UI 改 → 同步 Secret Manager |
| `lims-prod-django-secret-key` | 180 天 | `gcloud secrets versions add` → 重啟 backend → 所有 session 失效 |
| `lims-prod-db-password` | 365 天 | 改 Cloud SQL user 密碼 → 同步 Secret Manager → 重啟 backend |
| Cloud SQL 自動備份 | 自動 30 天 | Terraform 已設 |
| `GITOPS_PAT` | 90 天 | github.com 重產 PAT → 改 GitHub repo Secret |
| Lab manager / lab member 密碼 | 90 天 (建議) | UI 改 |

---

## F. 哪些東西絕對不能進 git

(都已經在 `.gitignore` 裡了,但這裡再 list 一次當 reminder)

- `.env`(實際的 docker-compose 用)
- `infra/envs/*/terraform.tfvars`(只有 `.tfvars.example` 進 git)
- `infra/envs/*/.terraform/`、`*.tfstate`、`*.tfstate.backup`
- 任何 `*.pem`、`*.key`、`*.json` 的 SA key 檔(我們用 Workload Identity,根本不應該下載 SA key)
- Argo CD 的 initial admin password
- DDNS provider 的密碼
