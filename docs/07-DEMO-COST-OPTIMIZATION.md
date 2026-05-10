# 07 · Demo 部署 — 成本控制 + 完整功能保留

期末 demo 用,**$300 GCP free credit 撐 ~1.5 個月**。所有功能 (frontend, backend, MySQL, Redis, Celery, observability, JWT auth, admin console) 都保留 — 只把 tier 縮小。

如果你之後要把這個變成 real production,看本文最後 **§F**。

---

## A. 預期月費(asia-east1)

| 項目 | 規格 | 月費 (USD) |
|---|---|---|
| GKE Autopilot control plane | 1 cluster | $73 |
| Pod CPU/RAM (1 backend + 1 frontend + 1 celery + migrate Job) | ~0.4 vCPU, 0.7 GiB | ~$25 |
| Cloud SQL MySQL | `db-custom-1-3840` ZONAL + 10GB SSD | ~$50 |
| Memorystore Redis | BASIC 1 GB | ~$40 |
| Cloud Load Balancer (HTTPS) | 1 forwarding rule | $18 |
| Static IP (in use) | 1 | $4 |
| Cloud NAT | minimal egress | $1 |
| Artifact Registry | ~5 GB images | $1 |
| Cloud Logging | < 50 GB/mo (free tier) | $0 |
| Managed Prometheus | < 50M samples/mo (free tier) | $0 |
| Cloud Trace | < 2.5M spans/mo (free tier) | $0 |
| **合計 / 月** | | **~$210** |

$300 credit ÷ $210/mo ≈ **1.4 個月**。

> 數字是估算 — 實際以 [Google Pricing Calculator](https://cloud.google.com/products/calculator) 為準。Network egress 以 demo 流量(< 1 GB / day)估算。

---

## B. 跟原本「Scenario A 真 prod」差在哪

| 項目 | Scenario A (原 prod) | Scenario B (demo) | 省 |
|---|---|---|---|
| Cloud SQL | `db-custom-2-7680` REGIONAL HA | `db-custom-1-3840` ZONAL | ~$150/mo |
| Memorystore | Standard 5 GB HA | Basic 1 GB | ~$260/mo |
| GKE Pods | 3 backend + 2 frontend HPA | 1 + 1 + 1 | ~$45/mo |
| Observability | self-hosted Prom + Loki + Tempo + Grafana | GCP managed (Logging + Prom + Trace) | ~$40/mo (含 6+ pods + GCS storage) |
| Binary Authorization | ENFORCE | DISABLED | $0 (無金錢成本,只少了 supply-chain 驗證) |
| Cloud Armor WAF | 自訂規則 | 預設 | $0 (rate limit 仍可單獨開) |
| **小計** | **~$700/mo** | **~$210/mo** | **節省 70%** |

**功能 (從 demo 角度看) 完全一樣** — frontend / backend / MySQL / Redis / Celery / 觀測 / JWT / multi-role / admin / 多實驗室 / Lot ID / WaferLot / Order pipeline 全在。

---

## C. 上線流程(用 Scenario B tier)

照原本的 [02-GCP-BRINGUP-RUNBOOK.md](02-GCP-BRINGUP-RUNBOOK.md) 走,因為 `infra/envs/prod/main.tf` 已經把 tier 全部設成 Scenario B 值。**你不用手動改 Terraform** — 直接 `terraform apply` 就會建小 tier。

唯一要改的是 GitHub repo 的 `terraform.tfvars`(填你 project ID + IP),以及 `helm/lims/envs/prod.yaml` 的 `cloudSql.connectionName` + `serviceAccount.gsaEmail`(從 Terraform output 抄)。

---

## D. 跑期間的成本控制

### D-1. 建 Billing 警報(必做)

Cloud Console → Billing → Budgets & alerts → CREATE BUDGET:
- Amount: USD **250** (留 $50 buffer)
- Threshold rules: 50% / 75% / 90% / 100% / 110%
- Notification: email 寄你

### D-2. 不用的時候 pause

Demo 結束後不打算再開 cluster?用 `make gcp-pause`:

```bash
make gcp-pause GCP_PROJECT=<your-project-id>
```

這會:
- `gcloud sql instances patch ... --activation-policy=NEVER` → Cloud SQL stop (vCPU/RAM 不收錢,只剩 storage ~$1.87/mo)
- `kubectl scale ... --replicas=0` → Autopilot pod 不收錢
- **GKE control plane 仍收 $73/mo** (Autopilot 沒辦法 stop,只能 destroy)
- **Memorystore 仍收 $40/mo** (沒有 stop,只能 destroy/recreate)
- **LB + IP 仍收 $22/mo**

Pause 期間月費降到大約 **$135**。

### D-3. resume

```bash
make gcp-resume GCP_PROJECT=<your-project-id>
```

會等 Cloud SQL state=RUNNABLE 再 scale pods 回來,避免 backend 起來時 Cloud SQL Auth Proxy 連不上。

### D-4. demo 完了直接 destroy 全部

```bash
make gcp-destroy GCP_PROJECT=<your-project-id>
```

跑 `terraform destroy`,把 cluster + Cloud SQL + Memorystore + IAM + IP 全部清掉。**$0/mo** (只剩 Artifact Registry storage ~$0.50,可手動刪)。

> ⚠️ Cloud SQL `deletion_protection` 已在 Scenario B prod 裡設成 false,所以 destroy 不會卡。資料一刪沒得救,demo data 沒差,但如果你想保留,先 export:
>
> ```bash
> gcloud sql export sql lims-prod-mysql gs://<bucket>/lims-final.sql.gz \
>   --database=lab_booking --project=<your-project-id>
> ```

---

## E. 30 天行事曆建議

```
Day  0       terraform apply               $0  (一次性 ~5 分鐘 GKE 建立)
Day  1-3     上線 + 修 bug                 ~$25
Day  4-25    demo 期(presentation 練習)    ~$150
Day 26       期末 demo 給老師看            (use day, ~$10)
Day 27-29    backup + 文件最後檢查         ~$15
Day 30       make gcp-destroy              $0
                                        ─────────
總計                                     ~$200 (在 $300 credit 內)
```

---

## F. 之後要變 real production

把 `infra/envs/prod/main.tf` 改回:

```hcl
module "cloudsql" {
  ...
  tier                = "db-custom-2-7680"
  availability_type   = "REGIONAL"
  deletion_protection = true
}

module "memorystore" {
  ...
  tier      = "STANDARD_HA"
  memory_gb = 5
}
```

然後改 `helm/lims/envs/prod.yaml`:

```yaml
backend:
  replicas: 3
  hpa: { min: 3, max: 10 }
frontend:
  hpa: { enabled: true, min: 2, max: 5 }
```

`terraform apply` 一次,Argo CD sync 一次。月費跳到 ~$700 但拿到 HA + 容錯 + 大規模流量處理。

如果還要更專業:
- 開 self-hosted observability stack(`gitops/applicationsets/observability.yaml`,設 `metrics.podMonitor.enabled=true`,`managedPrometheus.enabled=false`)
- Binary Authorization → ENFORCE
- Cloud Armor WAF rules(目前只有 GCLB 預設 protections)
- 第二 region cross-region replica(disaster recovery)
- Cloud SQL CMEK (customer-managed encryption keys)

---

## G. 出乎意料的成本來源(避免)

| 陷阱 | 為什麼貴 | 怎麼避免 |
|---|---|---|
| Cloud Logging > 50 GB/mo | 預設保留 30 天,每多 1 GB $0.50 | `DJANGO_LOG_LEVEL=INFO`(不是 DEBUG),且 demo 不要 stress test |
| Egress to internet | $0.12/GB outbound | 不要從 cluster 大量呼叫外部 API |
| 忘記關 dev/staging | 三倍錢 | Scenario B 範本只開 prod env (`infra/envs/dev/staging/` 不要 apply) |
| Static IP idle | 沒接 LB 仍收 $7.30/mo | terraform 跑完 LB 一定要 attach,或先別 reserve |
| Snapshot 累積 | Cloud SQL backup 超過 free tier | 30 天 retention 預設;不需要更長 |
| Container image bloat | Artifact Registry storage | 用 cleanup_policies 自動清(已設) |

---

## H. 如何追蹤實際花費

```bash
# 每天看一眼 (前一天到目前的費用)
gcloud billing accounts list --format="value(name,displayName)"
# 開 Cloud Console → Billing → Reports
# Filter by project: <your project>
# Group by: SKU description
```

最重的 SKU 應該照順序是:**Cloud SQL CPU → GKE Autopilot CPU → Memorystore → LB**。如果 SKU 排序跟這個不一樣,有東西在燒錢。

---

## I. demo 演示時跑什麼,讓觀眾看到「全功能」

照 [01-LOCAL-KIND-VALIDATION.md](01-LOCAL-KIND-VALIDATION.md) 的 §7 手稿,但是用 `https://lims.ddns.net/` 取代 `http://localhost:8080/`。流程:

1. **登入廠區帳號** (`testuser` / `Lims@2026!Init`) → 送樣表單 → 選實驗 + Lot ID 下拉 + 寫實驗需求 → 送出
2. **登入主管帳號** (`Lab_Mgr_Photo` / `Lims@2026!Init`) → 審核列表看到剛剛那筆 → 排程 + 指派機台 + 指派人員
3. **登入 lab member** (`Lab_Mem_Photo_001` / `Lims@2026!Init`) → 看任務 → 標記完成
4. **登入 admin** (`admin` / 你 Secret Manager 設的密碼) → 設備總覽看到狀態變動 → activity log 看到全程紀錄
5. **打開 Cloud Console → Monitoring → Metrics Explorer** → 即時看到 `prometheus.googleapis.com/django_http_requests_total_by_view_transport_method/counter` 這類 metric
6. **Cloud Console → Logging → Log Explorer** → 看到結構化 JSON log 跟 request_id 串起來
7. **Cloud Console → Trace** → 看到 SPA → backend → MySQL 的 trace
8. **Cloud Console → Kubernetes Engine → Workloads** → 看 pod、自己 selfHeal、HPA scale
9. **Argo CD UI** → 模擬 git push → 自動 sync → 部署完成

這些覆蓋:GKE workload + GitOps + observability + DB + cache + JWT auth + multi-role authorisation,所有非功能性需求一次到位。

---

## J. 總結

- **跑一個月 demo: ~$200,$300 credit 用得完不會超**
- **所有功能保留**,只是縮小 tier
- 用 GCP 內建 observability(Logging + Managed Prom + Trace)取代自架,省最大頭
- demo 結束 `make gcp-destroy` 一鍵清乾淨
- 中途不打算開可以 `make gcp-pause`,費率降到 ~$135/mo
- 之後要轉 real prod,改 5 行 Terraform + 3 行 Helm values 就好
