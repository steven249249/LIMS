# 04 · 日常維運手冊

LIMS 上線後的日常操作。這份不講「第一次怎麼建」(看 02-),講「跑起來之後遇到 X 怎麼辦」。

---

## 索引

- [A. 部署新版本](#a-部署新版本)
- [B. Rollback](#b-rollback)
- [C. 查狀態 + 看日誌](#c-查狀態--看日誌)
- [D. 改設定 (ConfigMap / Secret / Helm values)](#d-改設定)
- [E. 跑 Django 管理指令](#e-跑-django-管理指令)
- [F. Database 操作](#f-database-操作)
- [G. 加 / 改 / 刪使用者](#g-加--改--刪使用者)
- [H. 監控 / 告警 / Dashboard](#h-監控--告警--dashboard)
- [I. 處理常見故障](#i-處理常見故障)
- [J. 升級 chart / cluster / Cloud SQL](#j-升級-chart--cluster--cloud-sql)
- [K. 災難復原 (DR)](#k-災難復原-dr)
- [L. 暫停 / 恢復 (demo 省錢)](#l-暫停--恢復-demo-省錢)

---

## A. 部署新版本

正常流程 (前提:CI workflow 已啟用):

1. 工程師在 `lims` repo 開 PR → 改完 → merge 到 main
2. CI 跑 `cd.yml` → build image → push 到 Artifact Registry → 改 `gitops/envs/dev/values.yaml` 的 `image.tag` → push commit
3. Argo CD 偵測到 `lims-dev` Application out-of-sync → autoSync 啟動
4. PreSync `lims-lims-migrate` Job 跑 → 成功後 backend Deployment 滾動更新
5. **dev 自動完成。**

### Promote 到 staging

GitHub Actions 進 https://github.com/asddzxcc1856/LIMS/actions → 選 `CD (build → push → bump GitOps tag)` → **Run workflow** → 勾選 `promote_to_staging`。

需要在 GitHub 上先建一個叫 `staging` 的 Environment(Settings → Environments → New environment),裡面設一個 manual approval reviewer(你自己)。

### Promote 到 prod

prod 沒有 autoSync。流程是:

1. 在 staging 觀察 1-2 天 (`https://lims-staging.ddns.net/`),沒事再往下走
2. 開 PR 改 `gitops/envs/prod/values.yaml` 的 `image.tag` 成 staging 跑的那個 SHA
3. PR review → merge
4. **手動進 Argo CD UI** → `lims-prod` → SYNC

或 CLI:

```bash
argocd app sync lims-prod --prune
argocd app wait lims-prod --health --timeout 600
```

---

## B. Rollback

### B-1. 上一個版本剛上,發現有問題

**最快 (≤1 分鐘):** Argo CD UI → `lims-prod` → History → 選上一次的 sync → **Rollback**。

```bash
# CLI 等價
argocd app history lims-prod
# ID  DATE                       REVISION
# 12  2026-05-10T08:00:00+08:00  abc123def456
# 11  2026-05-10T07:00:00+08:00  789ghi012jkl
argocd app rollback lims-prod 11
```

### B-2. 多個版本之前 (git 層級)

```bash
cd "/media/hcis-s15/ssd2/Lab project"
# 找上次正常的 commit
git log --oneline gitops/envs/prod/values.yaml
git revert <bad-commit>
git push
# Argo CD 偵測到 → 你手動 sync
```

### B-3. 連 schema 都需要 rollback (DB 層)

如果新版本帶了破壞性 migration:

1. 先把 app rollback 到舊版 (B-1 / B-2)
2. **如果舊 app 跟新 schema 不相容**,需要從 Cloud SQL PITR 還原:

```bash
# Cloud Console → SQL → lims-prod-mysql → BACKUPS → Point in time
# 選個壞掉前的時間點 → CLONE → 給新 instance 一個名字,例如 lims-prod-mysql-rollback
```

3. 改 `helm/lims/envs/prod.yaml` 的 `cloudSql.connectionName` 指向新的 instance
4. commit + push + sync

---

## C. 查狀態 + 看日誌

### C-1. 全 cluster 概況

```bash
gcloud container clusters get-credentials lims-prod-gke \
  --region=asia-east1 --project=<your-project>

kubectl get pods -A | grep -v Running
# 期望輸出:空
```

### C-2. LIMS namespace

```bash
kubectl get all -n lims-prod
kubectl describe deployment lims-lims-backend -n lims-prod
kubectl top pods -n lims-prod                    # CPU/Memory 即時值
```

### C-3. Pod 日誌

```bash
# Live tail
kubectl logs -f -n lims-prod -l app.kubernetes.io/component=backend

# 上一個 (CrashLoop 看這個)
kubectl logs -n lims-prod <pod-name> -c app --previous

# Cloud SQL Auth Proxy sidecar (連不上 DB 時看)
kubectl logs -n lims-prod <pod-name> -c cloud-sql-proxy
```

### C-4. Cloud Logging (聚合所有 pod 的)

Cloud Console → Logging → Log Explorer → query:

```
resource.type="k8s_container"
resource.labels.namespace_name="lims-prod"
resource.labels.container_name="app"
severity>=ERROR
```

我們已經設成 JSON stdout (`DJANGO_PRODUCTION=True` 時),所以可以直接 query JSON field:

```
jsonPayload.request_id="abc123def456"   # 找特定請求的所有 log
jsonPayload.trace_id="..."              # 跨 service 串 trace
```

### C-5. Grafana 儀表板 (有跑 observability stack 的話)

- `https://grafana.internal.example.com` (你需要另外設 Ingress + auth,或 port-forward)
- 預設 admin: `admin` / `<applicationsets/observability.yaml 裡的 adminPassword>`
- 必看:
  - **kube-prometheus-stack / Kubernetes / Compute Resources / Namespace (Pods)** — pod CPU/Mem
  - **Django** (id 9528) — RPS, p95 latency, 5xx rate
  - **Loki / Logs / App** — 跨 pod 串日誌

---

## D. 改設定

### D-1. 改 ConfigMap (例如 log level、CORS、CSRF origin)

GitOps way:

1. 改 `helm/lims/envs/prod.yaml`,例如把 `DJANGO_LOG_LEVEL: INFO` 改成 `DEBUG`
2. commit + push
3. Argo CD sync (prod 是手動)
4. backend Deployment 自動 rolling update,因為 `checksum/config` annotation 變了

### D-2. 改 Secret (例如轉密碼)

1. **改 GCP Secret Manager:**
   ```bash
   echo -n "<new-value>" | gcloud secrets versions add lims-prod-django-secret-key \
     --data-file=- --project=<your-project>
   ```
2. ESO 預設 1 小時 refresh 一次。要立刻拿:
   ```bash
   kubectl annotate externalsecret -n lims-prod lims-lims-secrets \
     force-sync=$(date +%s) --overwrite
   ```
3. 等幾秒鐘確認 K8s Secret 更新:
   ```bash
   kubectl get secret -n lims-prod lims-lims-secrets -o jsonpath='{.data.DJANGO_SECRET_KEY}' | base64 -d
   ```
4. 重啟 backend(Secret 不會自動觸發 Deployment 滾動):
   ```bash
   kubectl rollout restart deployment -n lims-prod lims-lims-backend
   ```

### D-3. 改 replica count / HPA / 資源配額

改 `helm/lims/envs/prod.yaml` 的:
- `backend.replicas` (HPA 開的話會被覆蓋,看 `backend.hpa.min`)
- `backend.hpa.min` / `backend.hpa.max`
- `backend.resources.requests.cpu` 等

commit + push + sync。

---

## E. 跑 Django 管理指令

LIMS 有幾個自家 management command:

| Command | 用途 | 何時用 |
|---|---|---|
| `python manage.py migrate` | DB schema 升級 | Argo CD PreSync Job 自動跑 |
| `python manage.py collectstatic` | 收 static files | Dockerfile build 時跑 |
| `python manage.py ensure_admin` | 確保 superuser admin 存在 | 第一次部署時手動跑 |
| `python manage.py clear_orders` | 清空所有訂單 (含 `--diagnose-visibility`) | demo 環境重置 |
| `python manage.py reconcile_departments` | 合併重複 Department row | 資料不一致排查 |

### 跑法

```bash
# 1. 拿一個還沒跑滿的 backend pod
POD=$(kubectl get pod -n lims-prod -l app.kubernetes.io/component=backend \
  -o jsonpath='{.items[0].metadata.name}')

# 2. exec 進去
kubectl exec -it -n lims-prod $POD -c app -- \
  python manage.py ensure_admin

# 或 clear_orders
kubectl exec -it -n lims-prod $POD -c app -- \
  python manage.py clear_orders --diagnose-visibility
```

> ⚠️ `clear_orders` 會 **刪掉所有訂單** 並重設機台狀態。在 prod 跑之前確認你真的想要。

### 一次性 Job (大量 import / batch processing)

如果是會跑很久的 task,起一個 Job 比 exec 進 pod 安全:

```yaml
# /tmp/backfill.yaml
apiVersion: batch/v1
kind: Job
metadata: { name: lims-backfill, namespace: lims-prod }
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      serviceAccountName: lims-lims
      containers:
        - name: app
          image: asia-east1-docker.pkg.dev/<proj>/lims/backend:<current-tag>
          command: ["python", "manage.py", "<your-command>"]
          envFrom:
            - configMapRef: { name: lims-lims-config }
            - secretRef: { name: lims-lims-secrets }
          env: [{ name: DB_HOST, value: "127.0.0.1" }]
        # Cloud SQL Proxy
        - name: cloud-sql-proxy
          image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.2
          args: ["--private-ip", "--port=3306", "--quitquitquit", "<connectionName>"]
```

```bash
kubectl apply -f /tmp/backfill.yaml
kubectl logs -n lims-prod -l job-name=lims-backfill -f
```

---

## F. Database 操作

### F-1. 連到 Cloud SQL CLI

```bash
# 用 Auth Proxy 從你的工作站連 (假設 gcloud 已 login)
cloud-sql-proxy --private-ip <connection-name> &
mysql -h 127.0.0.1 -u lims_app -p lab_booking
# 密碼從 Secret Manager 拉:
#   gcloud secrets versions access latest --secret=lims-prod-db-password
```

### F-2. 從備份還原

Cloud Console → SQL → `lims-prod-mysql` → **Backups** 頁面:
- 每天的 automated backup
- PITR (任意秒)

點 **Restore** → 給新 instance 命名 → 等 ~10 分鐘。

### F-3. 抓 prod data 到 staging (需要先擦敏感資料)

```bash
# Cloud Console → SQL → lims-prod-mysql → 上方 EXPORT → 選 SQL → 寫到 GCS
# 然後在 staging instance IMPORT
# 中間最好用 CloudShell 跑一個 SQL 把使用者密碼洗掉:
#   UPDATE user SET password = '<dummy>';
```

---

## G. 加 / 改 / 刪使用者

詳見 [03-ACCOUNTS-AND-CREDENTIALS.md §C](03-ACCOUNTS-AND-CREDENTIALS.md#c-lims-內部使用者spa-登入)。

最快路徑:

```bash
# 進 admin console
https://lims.ddns.net/admin/users/
```

或 bulk 開:同頁面右上 **Bulk Create**。

---

## H. 監控 / 告警 / Dashboard

### H-1. Cloud Monitoring (GCP 內建)

預設已經收 cluster-level metric。建議加 alert policy:

| 名字 | Condition | Action |
|---|---|---|
| GKE node down | `up{job="kubernetes-nodes"} == 0` 持續 5m | PagerDuty |
| Cloud SQL CPU > 80% | metric 觸發 | Email + Slack |
| Cloud SQL DB connections > 80% capacity | 同 | Email |
| Memorystore memory > 80% | 同 | Email |
| Ingress 5xx > 1% | metric `loadbalancing.googleapis.com/https/request_count` | PagerDuty |

設法:Cloud Console → Monitoring → Alerting → CREATE POLICY。

### H-2. Prometheus 自訂 alert (有跑 observability stack 的話)

`gitops/applicationsets/observability.yaml` 裡的 kube-prom-stack 已經帶了 default alert。要加自家規則,寫一個 PrometheusRule CR:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: lims-app
  namespace: lims-prod
  labels: { release: kube-prometheus-stack }
spec:
  groups:
    - name: lims.app
      rules:
        - alert: BackendHighErrorRate
          expr: |
            sum(rate(django_http_responses_total_by_status_total{status=~"5..", app="backend"}[5m]))
            / sum(rate(django_http_responses_total_by_status_total{app="backend"}[5m])) > 0.01
          for: 5m
          labels: { severity: page }
```

### H-3. 應該每天看一眼的 dashboard

| 何時 | 看什麼 |
|---|---|
| 每天早上 | Argo CD UI → 確認所有 Application 是 `Healthy` + `Synced` |
| 每天早上 | Grafana → Django dashboard → 看昨天 24h 的 error rate / p95 |
| 每週 | Cloud Logging → severity>=ERROR → 檢查有沒有 spike |
| 每週 | Cloud SQL Insights → 慢 query top 10 |
| 每月 | Cloud Billing → 看花費,確認沒 leak |

---

## I. 處理常見故障

| 症狀 | 第一步 |
|---|---|
| 全站 503 | `kubectl get pods -n lims-prod`,看 backend 是不是都 NotReady |
| 全站 502 | Ingress 看不到 healthy backend → `kubectl describe ingress -n lims-prod`;通常是 readyz fail |
| 登入不行,500 | `kubectl logs -n lims-prod -l app=backend -c app --tail 50`;通常是 DB 連線斷 |
| 部分使用者看不到資料 | 部門 ID 不一致 → `kubectl exec -it -n lims-prod <pod> -c app -- python manage.py reconcile_departments --dry-run` |
| Migration Job stuck | `kubectl logs -n lims-prod -l app.kubernetes.io/component=migrate`,看是不是 lock 住 |
| Pod OOMKilled | 看 metrics 跟 `requests/limits` 不夠;改 `helm/lims/envs/prod.yaml` 的 resources |
| 突然 cert invalid | `kubectl describe managedcertificate -n lims-prod`;通常是 DDNS A record 沒指對 |
| HPA 沒 scale | `kubectl describe hpa -n lims-prod lims-lims-backend`;看是不是 metrics-server 壞了 |
| Argo CD 一直 OutOfSync | `argocd app diff lims-prod`;看到底差在哪 |

### Stuck 排序

如果 backend 全壞:

1. **先恢復服務**:rollback (B-1)
2. **隔離問題**:抓 log,問 root cause
3. **修源頭**:在 dev 修好 + test
4. **重來**:照 A 走流程

---

## J. 升級 chart / cluster / Cloud SQL

### J-1. Helm chart 改了

正常 PR 流程。Argo CD 會把 chart 變更套到 Application。

### J-2. GKE 升級

GKE Autopilot 預設在 REGULAR release channel,Google 自動升 minor version。**你要做的是看通知:**

- Pub/Sub topic (Terraform 設了 `notification_config.pubsub`) → 訂閱 → Email 你
- 升級期間 PDB 會被尊重 (我們的 backend `minAvailable: 2`),所以理論上沒中斷

### J-3. Cloud SQL 升級

Cloud SQL 的 maintenance_window 設在週日 18:00 UTC = 週一凌晨 02:00 台北。Google 可能在這個窗口推 patch 版本 (8.0.x.x → 8.0.x.x+1)。

**升 major version (8.0 → 9.0):**

```bash
gcloud sql instances patch lims-prod-mysql \
  --database-version=MYSQL_9_0
# 會中斷 ~5 分鐘
```

先在 staging 試。

---

## K. 災難復原 (DR)

### K-1. RPO / RTO 目標

| Data | RPO (能接受丟多久) | RTO (能接受 down 多久) |
|---|---|---|
| Database | 5 分鐘 (PITR) | 30 分鐘 |
| Pod state (沒持久化的 cache) | 0 (沒差) | 5 分鐘 |
| 全 cluster | 1 天 (Terraform 重建) | 4 小時 |

### K-2. 全 cluster 死掉的應變

1. **Cloud SQL 還在嗎?** 如果在 → data 沒丟。如果不在 (整個 region 出事) → 從 cross-region replica 推 failover (要先設,目前 Terraform 沒設)
2. **能再起一個 cluster:**
   ```bash
   cd infra/envs/prod
   terraform apply             # 如果原 cluster 還掛在 state 上會 in-place 修;否則重建
   ```
3. Argo CD 重 bootstrap (步驟 02-RUNBOOK §8)
4. `argocd app sync lims-prod` → 一切回來

### K-3. 整個 GCP project 不見了

少數機率場景,但有方法:

1. 開新 project + 重做 02-RUNBOOK 整套(需要 Terraform state — 所以 GCS state bucket 那個 versioning 很重要)
2. 從 Cloud SQL backup 在新 project 還原
3. DDNS A record 指到新 project 的 static IP

---

## L. 暫停 / 恢復 (demo 省錢)

Demo 模式下,如果你 1-3 天不會用 cluster,可以暫停 Cloud SQL + scale 0 pods,費率從 ~$210/mo 降到 ~$135/mo。**Memorystore 跟 GKE control plane 沒辦法暫停**(只能 destroy)。

### 暫停

```bash
# Set GCP_PROJECT once, or pass on every call
make gcp-pause GCP_PROJECT=<your-project-id>
```

底層做兩件事:
1. `gcloud sql instances patch lims-prod-mysql --activation-policy=NEVER` — Cloud SQL 停 vCPU/RAM,只剩 storage 計費
2. `kubectl scale -n lims-prod deployment --all --replicas=0` — Autopilot 停止 pod 計費

### 恢復

```bash
make gcp-resume GCP_PROJECT=<your-project-id>
```

會等 Cloud SQL state=RUNNABLE 才 scale pods 回來,避免 backend 起來時 Cloud SQL Auth Proxy 連不上 retry-loop。

### 完全 destroy(demo 結束)

```bash
make gcp-destroy GCP_PROJECT=<your-project-id>
```

**所有 GCP resource 全部 terminate,費率歸零。** Cloud SQL `deletion_protection` 在 Scenario B 已設 false 所以不會卡。

> ⚠️ 想保留 demo data:`gcloud sql export sql lims-prod-mysql gs://<bucket>/lims-final.sql.gz --database=lab_booking` 先 export 再 destroy。

---

## 附錄:常用 alias

放 `~/.bashrc`:

```bash
alias k='kubectl'
alias klogs='kubectl logs -n lims-prod'
alias kdesc='kubectl describe -n lims-prod'
alias limsexec='kubectl exec -it -n lims-prod $(kubectl get pod -n lims-prod -l app.kubernetes.io/component=backend -o jsonpath="{.items[0].metadata.name}") -c app --'

# 例如:
limsexec python manage.py shell
limsexec python manage.py ensure_admin
```
