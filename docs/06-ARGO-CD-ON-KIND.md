# 06 · Argo CD on kind (本地 GitOps 演練)

把 Argo CD 裝到 kind cluster,讓你在丟到 GCP 之前先看過 GitOps 流程的全貌:Application 物件、自動 sync、自我修復、rollback、UI 操作。

## 跟 kind-deploy 的差別

| | `make kind-deploy` (helm 直接裝) | Argo CD takeover |
|---|---|---|
| 誰跑 helm | 你的 host 端 | Argo CD repo-server pod |
| chart 從哪來 | 本地檔案 (`helm/lims/`) | GitHub `main` branch |
| sync 觸發 | 你手動 `make kind-deploy` | Argo CD 偵測 git → 自動 |
| rollback | `helm rollback` | Argo CD UI → History → Rollback |
| drift 修復 | 沒有 | `selfHeal: true` 自動還原 |

第一條路適合「我在改 chart 想立刻看效果」;第二條路是 **production 用的 flow**,值得在 kind 走過一次。

---

## 一、前置:乾淨 kind cluster

```bash
make kind-down                                      # 拆掉舊的(如果有)
make kind-up && make kind-deps && make kind-build && make kind-load
```

**注意:** **不要** 跑 `make kind-deploy`。我們要讓 Argo CD 從零裝,不要先有 helm release。

---

## 二、裝 Argo CD

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm install argocd argo/argo-cd -n argocd --create-namespace \
  --set 'configs.params.server\.insecure=true' \
  --version 7.7.6 --wait --timeout 5m
```

`server.insecure=true` 是因為 kind 沒有 TLS LB(GCP 上會有 GKE Ingress 處理)。

驗證:

```bash
kubectl get pods -n argocd
# 應該看到 argocd-server, argocd-application-controller-0, argocd-repo-server, etc. 全 Running
```

---

## 三、拿 admin 密碼

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d ; echo
```

複製這串。**第一次登入後立刻改掉**,然後刪掉這個 secret。

---

## 四、port-forward Argo CD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 9090:80
```

開瀏覽器 → **http://localhost:9090** → 用 `admin` + 上面那串密碼登入。

---

## 五、套用 LIMS Application

```bash
kubectl apply -f gitops/applications/lims-local.yaml
```

回到 Argo CD UI,你會看到一個 `lims-local` Application。

它應該會自動經歷:
1. **Sync Status:** OutOfSync → Syncing → Synced
2. **Health Status:** Missing → Progressing → Healthy

預期約 90 秒(主要是 migrate Job 把 27 筆 migration 跑完)。

### Sync wave 順序(設計重點)

```
wave -10:  ServiceAccount (略過 — local 沒建)
           ConfigMap (lims-lims-config)
           Secret (lims-lims-secrets)
                              ↓ Healthy
wave  -5:  migrate Job (Sync hook,跑完才會 +刪除)
                              ↓ Completed
wave   0:  Deployment backend, Deployment frontend, Services, Ingress (略過 — local 沒開), HPA, PDB
                              ↓ Healthy
            整個 Application 變 Healthy
```

這樣設計避免「migrate Job 在 ConfigMap 還沒建就啟動」的情況。

---

## 六、smoke test

```bash
curl http://localhost:8080/healthz
# ok

curl http://localhost:8080/readyz
# ok

curl -X POST http://localhost:8080/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Lims@2026!Init"}'
# {"refresh":"...","access":"..."}
```

或開瀏覽器 → http://localhost:8080/ → 用 `testuser` / `Lims@2026!Init` 登入。

---

## 七、操作 Argo CD UI 試試這幾件事

### 7-1. 看資源樹

點進 `lims-local` Application,左邊會顯示拓樸圖:Application → Deployment → ReplicaSet → Pod。每個 node 顯示 sync 狀態 + health 狀態。

### 7-2. 強制 sync

右上 SYNC 按鈕。可以勾選個別資源、可以 `Replace`、`Force`、`Prune`。

### 7-3. 模擬 drift,看 selfHeal 救回來

```bash
# 直接改 cluster 內的 Deployment
kubectl scale deployment lims-lims-backend -n lims-local --replicas=3
kubectl get pods -n lims-local | grep backend
# 你會看到 3 個 pod
```

回 Argo CD UI,等個 30 秒(預設 reconcile interval 是 3 分鐘,可以強制 refresh):

- Application 短暫變 OutOfSync
- selfHeal 啟動 → scale 回 1
- 變回 Synced

```bash
kubectl get pods -n lims-local | grep backend
# 又只剩 1 個
```

### 7-4. 模擬 rollback

UI 上方 **History and Rollback** 按鈕,看到所有 sync 紀錄。任何一個都可以點 Rollback。

CLI 版:

```bash
argocd login localhost:9090 --username admin --password <你的密碼>
argocd app history lims-local
argocd app rollback lims-local <revision-id>
```

---

## 八、模擬 GitOps deploy flow

完整模擬「工程師 push code → Argo 自動部署」:

1. 改任何一個 chart 的值,例如 `helm/lims/values.yaml` 的 `backend.replicas: 2`
2. `git commit -m "test: scale backend to 2"`
3. `git push`
4. 回 Argo CD UI,點 lims-local 右上的 **REFRESH**
5. Sync Status 變 OutOfSync
6. 因為 `automated.selfHeal: true`,Argo 自動 sync
7. 看到 backend 變成 2 replicas
8. 改回去 + push,reverse 一遍

production 上線後就是這個 flow,只是 git push 那邊由 CI 取代(`.github/workflows/cd.yml` 裡 `bump-dev-tag` job)。

---

## 九、清理

```bash
kubectl delete application -n argocd lims-local
helm uninstall argocd -n argocd
make kind-down                                # 連 cluster 一起拆
```

---

## 對應到 GCP 上線流程

GCP 上線的 [docs/02-GCP-BRINGUP-RUNBOOK.md](02-GCP-BRINGUP-RUNBOOK.md) 第 8 步是「Argo CD bootstrap」,流程跟上面 二 + 三 + 四 + 五完全一樣,只是:

- 用的不是 `gitops/applications/lims-local.yaml` 而是 `gitops/applicationsets/lims.yaml`(三個環境一次給)
- AppProject 那層 RBAC 也會套上(`gitops/projects/lims.yaml`)
- 加了 ESO + ClusterSecretStore 連到 GCP Secret Manager
- prod env 的 `autoSync: false` — 第一次 sync 是手動的

走過這個 kind 流程之後,GCP 那邊只是「規模放大 + 加管制」,概念一樣。
