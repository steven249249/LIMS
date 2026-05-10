# 01 · 本地 kind 驗證手冊

在實際丟到 GCP 之前,用本地 kind 跑一輪。這份步驟跟 `make kind-*` target 是一樣的,但拆開來方便你看每一步在做什麼、出問題時要看哪裡。

我已經確認過兩個 K8s image 都能 build 起來、單獨用 docker 跑 healthz 都回 200。下面要做的是把它們塞進 K8s 裡跟 mysql / redis 兜起來。

---

## 0. 前置工具安裝

我這邊沒有權限直接從網路下載 binary,請你裝這三個:

```bash
# kind v0.24.0
curl -Lo /tmp/kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
sudo install -m 0755 /tmp/kind /usr/local/bin/kind
kind version          # 應該印 kind v0.24.0 ...

# kubectl (跟 cluster 同版本即可,kind v0.24.0 預設帶 1.31)
curl -Lo /tmp/kubectl https://dl.k8s.io/release/v1.31.0/bin/linux/amd64/kubectl
sudo install -m 0755 /tmp/kubectl /usr/local/bin/kubectl
kubectl version --client

# helm 3
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version          # 應該印 v3.x
```

如果你不想 sudo,可以放在 `~/.local/bin` 並把它加進 PATH。

---

## 1. 確認 docker-compose 已關

```bash
cd "/media/hcis-s15/ssd2/Lab project"
docker compose ps        # 應該全空
```

我已經幫你 `docker compose down` 過了。如果還有殘留容器:

```bash
docker compose down -v   # -v 連 volume 也清掉
```

---

## 2. 起 kind cluster

```bash
make kind-up
```

這會跑 `kind create cluster --name lims-local --config scripts/kind-config.yaml`。配置會把 host 的 8080 port 對到 cluster 內的 NodePort 30080,讓你不用 port-forward 也能 curl。

**驗證:**
```bash
kubectl cluster-info --context kind-lims-local
kubectl get nodes
# NAME                       STATUS   ROLES           AGE
# lims-local-control-plane   Ready    control-plane   30s
```

---

## 3. 裝 in-cluster MySQL + Redis (取代 Cloud SQL / Memorystore)

```bash
make kind-deps
```

跑兩個 bitnami chart:

| Service | Address (cluster-internal) | 用途 |
|---|---|---|
| `lims-mysql` | `lims-mysql.lims-local.svc:3306` | 取代 Cloud SQL |
| `lims-redis-master` | `lims-redis-master.lims-local.svc:6379` | 取代 Memorystore |

**驗證:**
```bash
kubectl get pods -n lims-local
# NAME                READY   STATUS    AGE
# lims-mysql-0        1/1     Running   90s
# lims-redis-master-0 1/1     Running   90s
```

---

## 4. Build + 載入鏡像

```bash
make kind-build       # 跑兩個 docker build
make kind-load        # kind load docker-image lims/backend:local lims/frontend:local
```

`kind load` 會直接把 host 上的 image 複製到 kind node container 內,不用任何 registry。

**驗證:**
```bash
docker exec lims-local-control-plane crictl images | grep lims
# docker.io/lims/backend     local  ...
# docker.io/lims/frontend    local  ...
```

---

## 5. helm install LIMS

```bash
make kind-deploy
```

跑的是:
```bash
helm upgrade --install lims helm/lims/ \
  --namespace lims-local --create-namespace \
  -f helm/lims/envs/local.yaml \
  --set image.tag=local \
  --wait --timeout 5m
```

`envs/local.yaml` 已經把 cloudSql.enabled 設 false、externalSecrets.enabled 設 false、ingress.enabled 設 false,所以不需要 GCP 任何東西。

**會發生什麼:**

1. ConfigMap + 本地 Secret 建立
2. PreSync `migrate` Job 跑 `python manage.py migrate --noinput`(MySQL 第一次連線會跑全部 migration,包含 demo seed,因為 `SEED_DEMO_DATA=True`)
3. backend Deployment + frontend Deployment 起來
4. PodDisruptionBudget、HPA(disabled,replicas=1)、PodMonitor(disabled in local)套用

**第一次跑大概要 2 分鐘**(主要是 migrate Job 把 14 筆 migration 跑完)。

---

## 6. 確認狀態

```bash
make kind-status
```

預期:
```
── pods ─────────────────────────────────────────
NAME                              READY   STATUS      AGE
lims-lims-backend-xxxxxxxxx-xxx   1/1     Running     2m
lims-lims-frontend-xxxxxxxx-xxx   1/1     Running     2m
lims-lims-migrate                 0/1     Completed   2m
lims-mysql-0                      1/1     Running     5m
lims-redis-master-0               1/1     Running     5m
```

**Migration Job 應該是 `Completed`**(`0/1` 是 K8s 顯示「0 個容器還在跑」,Job 結束後是正常的)。

---

## 7. 功能驗證

### 7a. Health probe

```bash
make kind-test
```

會起一個 curl pod,從 cluster 內部打 `/healthz` + `/readyz`。預期兩個都 200。

### 7b. 從 host 打 backend

```bash
kubectl port-forward -n lims-local svc/lims-lims-backend 8000:8000 &
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:8000/metrics | head -20
kill %1
```

`/readyz` 應該回 `{"status": "ready", "checks": {"database": "ok", "redis": "ok"}}`。

### 7c. 從瀏覽器打整套 SPA + API

```bash
# 只需要一個 port-forward。nginx 自己代理 /api/*、/admin/*、/static/*
# 到 backend service,所以瀏覽器只要打 frontend 的 port 就好。
kubectl port-forward -n lims-local svc/lims-lims-frontend 18080:8080
```

> ⚠️ **一定要用 18080 不要用 8080。** host port 8080 容易撞到別的 listener
> (殘留的 docker compose、kind 自己的 NodePort handler 都會 listen 0.0.0.0:8080),
> 結果連線被 reset。任何 ≥ 10000 的閒置 port 都行。

開瀏覽器 → **http://localhost:18080/** → 登入畫面。

| Username | Password | Role | 可以做什麼 |
|---|---|---|---|
| `testuser` | `Lims@2026!Init` | 廠區使用者 | 送樣 (`/orders/create`)、看自己訂單 |
| `Lab_Mgr_Photo` | `Lims@2026!Init` | Photolithography Lab 主管 | 看 Photo lab 訂單、排程、指派 |
| `Lab_Mgr_Process` | `Lims@2026!Init` | Thin Film & Etch Lab 主管 | 同 Photo,範圍是 Process lab |
| `Lab_Mgr_QC` | `Lims@2026!Init` | Metrology & Inspection Lab 主管 | 同上 |
| `Lab_Mem_Photo_001` | `Lims@2026!Init` | Photo lab 成員 | 完成 Photo 的 stage |
| `Lab_Mem_Process_001` | `Lims@2026!Init` | Process lab 成員 | 完成 Process 的 stage |
| `Lab_Mem_QC_001` | `Lims@2026!Init` | QC lab 成員 | 完成 QC 的 stage |
| `admin` | `AdminLocal_2026!Init` | superuser | `/admin/` 全部 + Django `/django-admin/` |

> 全部 demo 帳號的密碼都是同一個 (`Lims@2026!Init`),由 [`backend/users/migrations/0003_create_demo_org.py:27`](backend/users/migrations/0003_create_demo_org.py#L27) 的 `DEFAULT_PASSWORD` 設。**只在 `SEED_DEMO_DATA=True` 時才會建這些帳號** — `helm/lims/envs/local.yaml` 已經設好了。
>
> `admin` 帳號的密碼則是來自環境變數 `LIMS_ADMIN_PASSWORD`,kind 模式下由 [`helm/lims/values.yaml`](helm/lims/values.yaml) 的 `localSecrets.limsAdminPassword` 提供。

### 7d. 測 admin 後台

兩個 admin:
- `https://localhost:18080/admin/` — 我們自己的 SPA admin console (用 admin 帳號 + JWT)
- `https://localhost:18080/django-admin/` — Django 內建 admin (用 admin 帳號 + session cookie)

兩個都可以,SPA admin 較好用。

---

## 8. 拆掉

```bash
make kind-down
```

整組 cluster 連同 pods、volume 全部清掉。host 不留任何狀態。

---

## 出問題的時候看哪裡

| 症狀 | 看這裡 |
|---|---|
| backend pod CrashLoop | `kubectl logs -n lims-local <pod> -c app` |
| migrate Job 失敗 | `kubectl logs -n lims-local job/lims-lims-migrate -c migrate` |
| readiness probe 一直失敗 | `kubectl describe pod -n lims-local <pod>` 看 events |
| MySQL 起不來 | `kubectl describe pod -n lims-local lims-mysql-0` 看是不是 disk 不夠 |
| `image not found` | `make kind-load` 沒跑;`docker images | grep lims` 確認 host 有 image,再 load 一次 |
| Helm 安裝住了 | `kubectl get pods -n lims-local`,看誰沒 Ready;事件可以 `kubectl get events -n lims-local --sort-by=.lastTimestamp` |

整個 kind 環境幾乎不會壞 — 出事就 `make kind-down && make kind-up` 重跑全套就好。
