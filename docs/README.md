# LIMS — 雲原生部署文件

從本地 → GCP 上線 → 日常維運的完整文件鏈。

## 文件結構

| 順序 | 檔案 | 何時看 |
|---|---|---|
| 1 | [01-LOCAL-KIND-VALIDATION.md](01-LOCAL-KIND-VALIDATION.md) | 還沒上 GCP,先在本機 kind 驗證 chart 跟 image 都對 |
| 2 | [02-GCP-BRINGUP-RUNBOOK.md](02-GCP-BRINGUP-RUNBOOK.md) | 第一次把整套丟到 GCP,從零開始的 step-by-step |
| 3 | [03-ACCOUNTS-AND-CREDENTIALS.md](03-ACCOUNTS-AND-CREDENTIALS.md) | 系統有哪些帳號、誰用什麼、初始密碼怎麼來、怎麼換 |
| 4 | [04-OPERATIONS-MANUAL.md](04-OPERATIONS-MANUAL.md) | 跑起來之後的日常:部署、rollback、查 log、改設定、災難復原 |
| 5 | [05-POST-SETUP-NOTES.md](05-POST-SETUP-NOTES.md) | 上線後 24 小時 / 1 週內必做的硬化動作 + 常見雷 |
| 6 | [06-ARGO-CD-ON-KIND.md](06-ARGO-CD-ON-KIND.md) | 在本機 kind 演練 Argo CD GitOps flow,丟 GCP 前先看過 |
| 7 | [07-DEMO-COST-OPTIMIZATION.md](07-DEMO-COST-OPTIMIZATION.md) | **Demo 用** Scenario B 成本拆解、暫停 / destroy 流程、撐 1 個月行事曆 |

## 快速 navigation

**「我要做期末 demo,成本要控制」** → 07 → 02 → 03

**「我要上線真 prod」** → 02 → 03 → 05 → 07 §F

**「上線完了,日常用」** → 04

**「壞了」** → 04 §I (Common failures)

**「demo 結束想關掉」** → 04 §L 或 07 §D-2

**「拿到代碼想理解架構」** → repo 根目錄 [CLOUD_NATIVE_CHECKLIST.md](../CLOUD_NATIVE_CHECKLIST.md) + [helm/lims/README.md](../helm/lims/README.md)

## 同時存在的兩個 deployment 路徑

這個 repo 目前同時支援兩套部署:

| 路徑 | Dockerfile | 用途 |
|---|---|---|
| **legacy docker-compose** | `backend/Dockerfile` + `frontend/Dockerfile` (Caddy) | 你既有的 lims.ddns.net 部署。已經被 GKE 取代,但留著當 fallback |
| **GKE (新)** | `backend/Dockerfile.k8s` + `frontend/Dockerfile.k8s` (nginx) | 新世代;這份文件講的就是這個 |

GKE 上線、跑穩 7 天後可以把 legacy 路徑的檔案刪掉。
