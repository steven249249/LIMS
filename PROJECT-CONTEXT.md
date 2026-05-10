# LIMS — Project Context Prompt

複製整份貼給任何 AI / 新進工程師,即可拿到完整專案上下文。本文件會跟程式碼一起 commit,作為持續的 source of truth。

---

## 你接手的是什麼專案

LIMS (Lab Information Management System) — 一個給半導體 fab 用的晶圓送樣 + 排程系統。架構:Vue 3 SPA + Django REST + MySQL + Redis + Celery,以 GitOps 方式部署在 GKE Autopilot 上,使用 lims.ddns.net 對外。

期末 demo 用的部署規格(Scenario B): ~$210/月,$300 GCP free credit 撐 ~1.5 個月,所有功能保留。

---

## 領域模型 (絕對不要破壞的 invariant)

**四種角色** (`backend/users/models.py:User.Role`):
- `regular_employee` (廠區使用者) — 送樣;**只看自己訂單,不看任何機台資訊**
- `lab_manager` (主管) — 看自己實驗室的訂單 + 排程 + 指派人員/機台
- `lab_member` (成員) — 看指派給自己的 stage,完成回報
- `superuser` — 全域管理員

**訂單流程** (`backend/orders/services.py`):
1. 廠區使用者選 Experiment + 從 WaferLot 下拉選 Lot ID + 寫實驗需求 → 送出 Order
2. Order 自動 route 到該 Experiment 對應的實驗室
3. 主管在審核列表看到 → 排日期 + 指派人員 + (可選)指派機台
4. 成員完成 stage → Order DONE
5. **一張訂單 = 一個實驗室的訪問**;多站需求由廠區再送一次新訂單

**Hard invariants — 絕對不要違反:**
- 一個 Experiment 釘一個 Department (`Experiment.department` 必填,不是 optional tag)
- 一個 Order 只有一個 OrderStage(不再有跨實驗室 relay)
- `Order.department == OrderStage.department == Experiment.department`(主管可視性 query 靠這個對齊)
- `WaferLot.code` 是 primary key(全域唯一),`Order.lot` 是 FK 不是 free-text
- 廠區使用者送樣表單只有「實驗類型 / Lot ID 下拉 / 實驗需求 / 備註 / 緊急」,**不顯示機台類型 / 機台代碼 / 接力進度**
- `/equipment` 路由只有 lab_manager / superuser 能進;manager 只看自己 lab 的機台
- demo 帳號 (`testuser`, `Lab_Mgr_*`, `Lab_Mem_*`) 只在 `SEED_DEMO_DATA=True` 時建,prod 預設 False;`admin` 帳號永遠建,密碼來自 `LIMS_ADMIN_PASSWORD` env

---

## Tech stack (具體版本)

| 層 | 細節 |
|---|---|
| Backend | Django 5.2 + DRF 3.17 + simplejwt 5.5 + django-cors-headers 4.9 + django-prometheus 2.4 + WhiteNoise 6.7 + python-json-logger 4 |
| DB driver | PyMySQL 1.1 + cryptography(MySQL 8 caching_sha2_password 必要) |
| Redis | Cache backend `django.core.cache.backends.redis.RedisCache` + Celery 5.6 broker(同一 instance) |
| Frontend | Vue 3 + Vite 8 + Ant Design Vue + vue-i18n(zh-TW + en) + axios + dayjs + Playwright e2e |
| Image | `python:3.11-slim` builder→runtime,UID 10001 non-root,readOnlyRootFilesystem;`nginx:1.27-alpine` 同樣 non-root,nginx pid 寫 `/tmp` |
| K8s | Helm chart 14 個 templates(Deployment, Service, Ingress, ManagedCertificate, BackendConfig, FrontendConfig, HPA, PDB, NetworkPolicy, PodMonitor, ManagedPrometheusPodMonitoring, ConfigMap, ExternalSecret, Job, ServiceAccount) |
| Infra | Terraform 1.7+ + google provider ~5.40 — modules: network, gke, cloudsql, memorystore, artifact-registry, iam |
| GitOps | Argo CD ApplicationSet + AppProject;sync waves: -10 (config/secret/SA) → -5 (migrate Job, Sync hook) → 0 (deployments) |
| Observability | GCP Managed Prometheus + Cloud Logging + Cloud Trace (demo);自架 kube-prom-stack + Loki + Tempo + OTel Collector 為 optional(`gitops/applicationsets/observability.yaml`) |
| CI | GitHub Actions:lint + 112 backend pytest + frontend vitest + e2e Playwright + Trivy scan + push to Artifact Registry + bump gitops tag(全部 keyless 透過 Workload Identity Federation) |

---

## Repo 結構

```
backend/                Django + Dockerfile.k8s (K8s) + Dockerfile (legacy docker-compose)
  backend/              Django settings + health.py (/healthz, /readyz)
  users/                User, FAB, Department, WaferLot
  orders/               Order, OrderStage, services.py (create_order, complete_stage, …)
  equipments/           Experiment, EquipmentType, Equipment, ExperimentRequiredEquipment(legacy 保留)
  scheduling/           EquipmentBooking, allocate_equipments_for_stage
  monitoring/           ActivityLog, RequestIDMiddleware
  admin_api/            superuser CRUD endpoints
  utils/                logging_filters (CorrelationFilter), exception_handler
  tests/                112 tests,factories,conftest
  staticfiles/.gitkeep  WhiteNoise collectstatic 目標(Dockerfile.k8s build 時填入)

frontend/               Vue SPA + Dockerfile.k8s (nginx) + nginx.k8s.conf + Dockerfile (Caddy legacy)
  src/views/{requester,manager,member,admin}/  各角色頁面
  src/i18n/{zh-TW,en}.js
  src/api/{client,users,orders,equipments,scheduling,admin}.js

helm/lims/              Helm chart
  Chart.yaml, values.yaml(production-leaning defaults)
  envs/{local,dev,staging,prod}.yaml      per-env overrides
  templates/*.yaml      14 個 K8s templates

infra/                  Terraform IaC
  modules/{network,gke,cloudsql,memorystore,artifact-registry,iam}
  envs/{dev,staging,prod}/{main.tf,variables.tf,terraform.tfvars.example}

gitops/                 Argo CD GitOps
  projects/lims.yaml                       AppProject (RBAC scope)
  applicationsets/{lims,observability}.yaml ApplicationSet × 2
  applications/lims-local.yaml              kind 用單獨 Application
  envs/{dev,staging,prod}/values.yaml       CI 自動 bump image.tag

scripts/
  kind-config.yaml      kind cluster 配置(host 8080 → node 30080)
  kind-deps.yaml        in-cluster mysql:8.0 + redis:7-alpine(取代 bitnami,因為 bitnami 公開鏡像下架了)

.github/workflows/
  ci.yml                push/PR:lint → pytest → vitest → e2e → build
  cd.yml                main push:build → push to Artifact Registry → Trivy → bump gitops/envs/dev/values.yaml

docs/                   操作手冊 7 份
  01-LOCAL-KIND-VALIDATION.md       本地 kind 驗證
  02-GCP-BRINGUP-RUNBOOK.md         GCP 從零上線(11 step)
  03-ACCOUNTS-AND-CREDENTIALS.md    四層帳號 + 密碼 + 輪替
  04-OPERATIONS-MANUAL.md           日常維運(含 §L 暫停/恢復)
  05-POST-SETUP-NOTES.md            上線後 24h/1w 硬化清單
  06-ARGO-CD-ON-KIND.md             本地演練 Argo CD GitOps
  07-DEMO-COST-OPTIMIZATION.md      Scenario B 成本拆解 + 30 天行事曆
  README.md                         索引

Makefile                kind-{up,down,deps,build,load,deploy,status,test} + gcp-{pause,resume,destroy}
CLOUD_NATIVE_CHECKLIST.md  REPLACE-ME 速查
PROJECT-CONTEXT.md      本文
```

---

## 部署路徑

1. **Legacy docker-compose** (`docker-compose.yml`) — 仍在 `lims.ddns.net` 跑(用家裡 IP 的 DDNS),被新版取代後可廢棄
2. **本地 kind 驗證** — `make kind-up && kind-deps && kind-build && kind-load && kind-deploy`,然後 `http://localhost:8080`(NodePort 30080)
3. **本地 kind + Argo CD GitOps 演練** — 多裝 Argo CD,套 `gitops/applications/lims-local.yaml`,看 sync waves 跑完。文件 06
4. **GCP demo (Scenario B, ~$210/月)** — 預設 Terraform/Helm 值已調好。文件 02 + 07
5. **GCP real prod (Scenario A, ~$700/月)** — Cloud SQL HA + Memorystore Standard 5GB + 自架 observability。文件 07 §F 的 5 行 Terraform diff

DDNS:`lims.ddns.net` A record 指向 `terraform output ingress_static_ip_address`(目前還指家裡 IP,GCP cluster 起來後切過去)。

---

## 帳號

**Demo seed 帳號**(`SEED_DEMO_DATA=True` 才建,密碼皆為 `Lims@2026!Init`):
- `testuser` — regular_employee, Photo lab
- `Lab_Mgr_Photo` / `Lab_Mgr_Process` / `Lab_Mgr_QC` — lab_manager
- `Lab_Mem_Photo_001` / `Lab_Mem_Process_001` / `Lab_Mem_QC_001` — lab_member

**永遠建的 superuser**:
- `admin`,密碼來自 `LIMS_ADMIN_PASSWORD` env(本地 kind = `AdminLocal_2026!Init`,prod = Secret Manager `lims-prod-lims-admin-password`)

詳細 → docs/03

---

## 指令速查

```bash
# 後端測試
cd backend && pytest --no-header -q       # 期望:112 passed

# 前端 build
cd frontend && npm run build

# 本地 K8s 驗證(整套)
make kind-up && make kind-deps && make kind-build && make kind-load && make kind-deploy
# 然後 http://localhost:8080,登入 testuser/Lims@2026!Init

# 本地拆掉
make kind-down

# GCP 暫停 / 恢復 / 完全 destroy
make gcp-pause GCP_PROJECT=<id>      # 降到 ~$135/月
make gcp-resume GCP_PROJECT=<id>
make gcp-destroy GCP_PROJECT=<id>    # $0/月
```

---

## 還沒做的事(下一輪 work scope)

- [ ] 使用者親自跑 docs/02 把 GCP project 開起來(需要他的 billing account + 工作站 IP)
- [ ] DDNS A record 從家裡 IP 切到 GCLB static IP
- [ ] Argo CD 在 GKE cluster 上 bootstrap(目前只在本地 kind 驗證過)
- [ ] 第一次手動 sync `lims-prod`(prod 沒 autoSync)
- [ ] 等 ManagedCertificate 變 Active(15-60 分鐘)
- [ ] Smoke test https://lims.ddns.net 全部功能 + 觀測性
- [ ] 上線後 admin 密碼立刻換掉(docs/05 §A)
- [ ] (可選)Celery 加實際 `@shared_task`,目前 worker pod idle

---

## 維護慣例

- **commit 風格** — imperative subject、body 講 "why" 不講 "what"、附 `Co-Authored-By: Claude Opus 4.7`
- **絕不 `git push --force` main**;rollback 用 `git revert`
- **secret 從不入 git**(`.env` 已 gitignore;CI 用 ESO + Secret Manager + Workload Identity)
- **image tag = git short SHA**(12 chars),Artifact Registry 已啟用 immutable tags
- **CD 從不直接 `kubectl apply`**,只 bump tag 然後讓 Argo CD 拉
- **所有 chart 變更要 `helm template` + 在 kind 跑過再 push**
- **新欄位 / 新表 → migration 必經;`SEED_DEMO_DATA` env-gate 任何 demo data**
- **commit 前跑 `cd backend && pytest`**,112 個測試必須全綠

---

## 對話風格(專案維持的個性)

- 中文回覆 (zh-TW)
- 簡短具體,每個 claim 都對應到實際檔案 (file:line 格式)
- 不堆敬辭 / 不灑滿 emoji / 不長篇 summary
- 多用 TodoWrite 追進度
- 模糊時先問一次,然後標記假設後繼續做
- 不超出需求加功能、不過度抽象
- code 永遠優先,文件其次

---

## 重要決策歷史(避免被推翻)

1. **MySQL 不切 Postgres** — codebase 沒有 vendor-specific 查詢,Cloud SQL for MySQL 完全支援,切換沒有上行收益
2. **Helm + ApplicationSet 而不是純 kustomize** — Helm values per-env 對應 Argo generator 最自然
3. **送樣表單從多階段 pipeline 改成單站** — 每個 Order 一個 lab visit,跨 lab 由廠區再送新單
4. **WaferLot 用 code 當 PK 而不是 UUID + code unique** — 用戶明確要求 "Lot ID is primary key and unique"
5. **Demo 觀測性用 Cloud managed 而不是自架** — 省 ~$40/月,demo 演示 UX 等價
6. **Cloud SQL Auth Proxy 跑 sidecar 而不是 Service** — Workload Identity 最乾淨
7. **legacy `Dockerfile` (Caddy + ACME) 跟 `Dockerfile.k8s` (nginx) 並存** — docker-compose 部署不被破壞,GKE 用新版
8. **bitnami chart 不能用** — 公開鏡像下架,改自家 `scripts/kind-deps.yaml` 用 mysql:8.0 + redis:7-alpine
9. **NetworkPolicy 在 kind 模式關掉** — kindnet 1.31 真的會 enforce,擋了 in-cluster MySQL :3306,只在 prod 開
10. **migrate Job 是 Sync hook 不是 PreSync** — PreSync 跑在所有 sync wave 之前,ConfigMap 還沒建,所以改 Sync + sync-wave -5,搭配 ConfigMap/Secret/SA 的 sync-wave -10
