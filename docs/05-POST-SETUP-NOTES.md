# 05 · 設置完成後的注意事項 (gotchas + checklist)

跑完 02-RUNBOOK 全部步驟之後 **24 小時內** 必做的事,以及容易踩到的雷。

---

## A. 上線當天的 checklist (照順序做)

### A-1. 立刻換掉 admin 密碼 (T+0)

**為什麼:** Secret Manager 裡的初始密碼是你在 02-步驟 4 用的字串,如果你那時用了 `ChangeMe_2026!Admin` 之類的,任何看得到 git history 或這份文件的人都猜得到。

```bash
# 1. 登入 https://lims.ddns.net/django-admin/  (帳號 admin / 初始密碼)
# 2. 改 admin 帳號密碼
# 3. 同步 Secret Manager:
echo -n "<新密碼>" | gcloud secrets versions add lims-prod-lims-admin-password \
  --data-file=- --project=<your-project>
```

### A-2. 確認所有 secret 都不是預設值 (T+1h)

```bash
# 隨便 cat 出來看一眼,確認不是 placeholder 字串
for s in django-secret-key db-password lims-admin-password redis-auth; do
  echo "── lims-prod-$s ──"
  gcloud secrets versions access latest --secret=lims-prod-$s | head -c 20; echo "..."
done
```

每個都應該長得像隨機字串,不是 `REPLACE-ME` 或 `kind-only` 這種。

### A-3. 把 demo seed data 從 prod DB 清掉 (如果有)

`SEED_DEMO_DATA=False` 應該擋住 demo 帳號被建,但如果你不小心開過 True 跑過一次 migrate:

```bash
limsexec python manage.py shell -c "
from users.models import User
User.objects.filter(username__in=[
  'testuser', 'Lab_Mgr_Photo', 'Lab_Mem_Photo_001',
  'Lab_Mgr_Process', 'Lab_Mem_Process_001',
  'Lab_Mgr_QC', 'Lab_Mem_QC_001'
]).delete()
"
```

### A-4. 檢查 cluster 的 master_authorized_networks (T+1h)

```bash
gcloud container clusters describe lims-prod-gke \
  --region=asia-east1 --format="value(masterAuthorizedNetworksConfig.cidrBlocks)"
```

只應該有你的 IP。如果出現 `0.0.0.0/0` 馬上改 `infra/envs/prod/terraform.tfvars` 然後 `terraform apply`。

### A-5. 啟用 GCP audit logging Data Access logs (T+24h)

預設只開 Admin Activity logs (誰建了 cluster 之類)。要看「誰讀了哪個 secret」需要開 Data Access logs:

Cloud Console → IAM → **Audit Logs** → 找 **Cloud Secret Manager API** → 勾 `Data Read` + `Data Write` → SAVE。

### A-6. 設 Billing 警報 (T+24h)

Cloud Console → Billing → **Budgets & alerts** → CREATE BUDGET:
- 預算金額:每月 USD 200 (示意,看你預期)
- Threshold: 50%, 90%, 100%
- Email recipients: 你

避免 cluster 被打 / DB 設錯 tier 導致月底 GG。

### A-7. DDNS A record 自動續租?

`*.ddns.net` 通常 30 天不登入就釋放 hostname。**進 DDNS provider 設 auto-renew,或設個 calendar reminder 30 天登一次。**

---

## B. 容易踩的雷

### B-1. ManagedCertificate 卡 Provisioning

最常見原因:DDNS A record 還沒生效。確認:

```bash
dig +short lims.ddns.net
# 必須等於 terraform output ingress_static_ip_address
```

第二常見:`spec.domains` 拼錯。`kubectl describe managedcertificate -n lims-prod lims-lims-cert`,看 events。

### B-2. Argo CD 一直 OutOfSync 但 diff 看不出哪裡不一樣

通常是 ManagedCertificate `.status` 在 Google 那邊一直更新,我們已經在 ApplicationSet 裡 `ignoreDifferences` 掉了 — 但有可能是別的 resource。Run:

```bash
argocd app diff lims-prod
```

看到 diff 之後,如果是 server-managed field (例如 `metadata.generation`),加進 `ignoreDifferences`。

### B-3. Cloud SQL Auth Proxy 連不上 (`error 9: dial: lookup ...`)

可能原因:
1. `cloudSql.connectionName` 拼錯 — 必須完全等於 `terraform output cloudsql_connection_name`
2. runtime SA 沒有 `roles/cloudsql.client` — `gcloud projects get-iam-policy` 確認
3. Workload Identity 沒綁好 — `kubectl describe sa lims-lims -n lims-prod`,看 annotation 是不是對

### B-4. Pod OOMKilled

backend 預設 `limits.memory: 1Gi`。如果 Sentry / OTel SDK 開到全力 trace,可能不夠。改 `helm/lims/envs/prod.yaml`:

```yaml
backend:
  resources:
    limits:
      memory: 2Gi
```

### B-5. Cloud SQL 用滿 connection pool

Django 預設 `CONN_MAX_AGE: 0` (每個 request 開新 connection)。在 K8s + 高 RPS 下會打爆 Cloud SQL 的 connection limit。

修法:`backend/backend/settings.py` 加:

```python
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
```

或裝 PgBouncer/ProxySQL sidecar。

### B-6. `kubectl` 連不上 cluster (Master Authorized Networks)

如果你換家上網 (公司 → 家裡),你的 public IP 變了,master 會擋你:

```bash
# 取目前 IP
MY_IP=$(curl -s https://api.ipify.org)
# 加進 authorized_networks
cd infra/envs/prod
# 編 terraform.tfvars,加一個 entry:
#   "operator-home-2" = "$MY_IP/32"
terraform apply
```

或 emergency 用 Cloud Console → GKE → Cluster → Networking → 直接編 Master authorized networks。

### B-7. Helm `--wait` timeout 但 pod 其實是好的

K8s 的 Service Discovery 慢, readiness probe 預設 5s 起跳 + periodSeconds 10s。第一次部署可能要 60-90 秒才 Ready。`make kind-deploy` 給 `--timeout 5m`,但 helm CLI 預設只有 5 分鐘,不夠就要拉長。

---

## C. 安全加固 (T+1 week 該做)

### C-1. Cloud Armor WAF policy

Terraform 沒建 — 因為要 trial-and-error tune。手動建:

```bash
# 預設 deny 所有 OWASP top 10 attempt
gcloud compute security-policies create lims-prod-armor \
  --description="LIMS WAF policy"

# rate limit (per IP)
gcloud compute security-policies rules create 100 \
  --security-policy=lims-prod-armor \
  --src-ip-ranges="*" \
  --action=throttle \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action=allow --exceed-action=deny-429

# OWASP top 10 — XSS / SQLi / Local File Inclusion preconfig
gcloud compute security-policies rules create 1000 \
  --security-policy=lims-prod-armor \
  --src-ip-ranges="*" \
  --action=deny-403 \
  --expression="evaluatePreconfiguredExpr('xss-stable')"
```

然後 `gitops/applicationsets/lims.yaml` 的 BackendConfig 已經 reference 這個 policy 名 — sync 之後會自動 attach。

### C-2. Binary Authorization 嚴格模式

Terraform 已經設 prod 為 `PROJECT_SINGLETON_POLICY_ENFORCE`,但 policy 本身是 ALLOW_ALL。要嚴格簽名驗證:

```bash
# 1. 建 attestor
gcloud container binauthz attestors create ci-attestor \
  --attestation-authority-note=projects/<proj>/notes/ci-note \
  --description="CI build attestor"

# 2. 建 policy 限 image 必須有 attestation
cat > policy.yaml <<EOF
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
    - projects/<proj>/attestors/ci-attestor
EOF
gcloud container binauthz policy import policy.yaml
```

### C-3. 改 Argo CD admin → SSO

預設只有 `admin` 帳號。建議綁到 GitHub:

```yaml
# argocd-cm ConfigMap
data:
  url: https://argocd.lims.ddns.net
  dex.config: |
    connectors:
      - type: github
        id: github
        name: GitHub
        config:
          clientID: <oauth-app-id>
          clientSecret: $dex.github.clientSecret
          orgs:
            - name: <your-github-org>
```

### C-4. NetworkPolicy egress lockdown

我們的 `helm/lims/templates/networkpolicy.yaml` 用 `0.0.0.0/0` 開放 Cloud SQL egress (因為 Cloud SQL public IP 範圍很雜)。要更嚴可以:

1. 關掉 `ipv4_enabled` (Terraform 已關),確認真的 private only
2. egress 改成只開 `psa_cidr` (Terraform output 已給),不開 0.0.0.0/0

---

## D. 日後成本控制

### D-1. 已知會花錢的東西

| Resource | 月費 (asia-east1, 估) |
|---|---|
| GKE Autopilot cluster | $73 (control plane) + pod usage |
| Cloud SQL `db-custom-2-7680` REGIONAL | ~$200 (HA) |
| Memorystore Redis Standard 5GB | ~$70 |
| Static IP (reserved, idle) | $7.30 |
| Cloud Logging | 每 GB 寫入 $0.50 (前 50GB 免費) |
| Cloud Trace | 每 100 萬 span $0.20 |
| Egress to internet | 看流量 |

**全部加起來 prod 月費 ~$400-500 USD。**

### D-2. 省錢路線

- dev/staging 用 ZONAL 不用 REGIONAL Cloud SQL → 省一半
- dev/staging 用 BASIC Memorystore 而不是 STANDARD_HA → 省一半
- 不用 24/7 跑 cluster:晚上 / 假日 scale 到 0 (`gcloud container clusters resize ... --num-nodes=0`)
- Cloud SQL 也可以 stop:`gcloud sql instances patch <name> --activation-policy=NEVER`,要用時 ALWAYS

寫成腳本:

```bash
# scripts/lims-prod-pause.sh
gcloud sql instances patch lims-prod-mysql --activation-policy=NEVER --quiet
# resume:
# gcloud sql instances patch lims-prod-mysql --activation-policy=ALWAYS --quiet
```

但別在生產這樣搞,只 dev/staging 用。

---

## E. 文件之間的關係

```
docs/
├── 01-LOCAL-KIND-VALIDATION.md     ← 第一次跑;確認 chart + image OK
├── 02-GCP-BRINGUP-RUNBOOK.md       ← 從零建 GCP infra + 第一次部署
├── 03-ACCOUNTS-AND-CREDENTIALS.md  ← 哪些帳號、誰用、怎麼改
├── 04-OPERATIONS-MANUAL.md         ← 跑起來之後的日常維運
└── 05-POST-SETUP-NOTES.md          ← (本文) 上線後的 todo + 雷區
```

CLOUD_NATIVE_CHECKLIST.md (repo root) 是 02 的精簡版 — 只條列要填 REPLACE-ME 的地方,不講 step-by-step。

---

## F. 把這份文件當 SLA 起點

把上面 §A 的 7 點變成 OKR / 上線驗收條件。沒做完不算上線完成。

```
[ ] T+0   admin 密碼換掉
[ ] T+1h  所有 secret 確認不是預設值
[ ] T+1h  prod 沒有 demo seed 資料
[ ] T+1h  master_authorized_networks 只有自己 IP
[ ] T+24h GCP audit logs Data Access 開啟
[ ] T+24h Cloud Billing 警報設好
[ ] T+24h DDNS auto-renew 設好
[ ] T+1w  Cloud Armor policy 套上
[ ] T+1w  Binary Authorization 從 PERMISSIVE 切 ENFORCED
[ ] T+1w  Argo CD admin 綁 SSO
```
