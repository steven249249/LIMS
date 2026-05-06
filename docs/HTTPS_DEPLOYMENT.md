# LIMS HTTPS 部署指南 (lims.ddns.net)

把 LIMS 從 `http://lims.ddns.net` 升級到 `https://lims.ddns.net:443`,
**全程約 5 分鐘**(假設 docker / docker compose 已裝好,DNS 已指對)。

---

## 一、預先檢查清單

在伺服器上執行升級前,確認下列三件事:

### 1. 公網可達

```bash
# 在伺服器上跑,確認 80 + 443 都沒被防火牆擋:
sudo ss -tlnp | grep -E ':80|:443'
# 應該看到舊的 nginx (port 80) 在跑;或全空 — 升級流程會接管
```

從**外網**試 ping:
```bash
# 從別的網路 (手機 4G 也行) 跑:
curl -I http://lims.ddns.net
# 任何回應(包括 connection refused / 404)代表 80 通到伺服器;
# 真正 timeout 才是路由器/防火牆有擋。
```

### 2. DNS 解析正確

```bash
dig +short lims.ddns.net
# 應該回傳該伺服器的公網 IP。如果這台機器在 NAT 後面,
# 確認 router 已做 port forward 80 + 443 到這台機器的內網 IP。
```

DDNS 常見問題:DDNS 客戶端(no-ip / dynu / DuckDNS 等)有沒有自動更新 IP?
若伺服器 IP 變了 DDNS 沒跟上,Let's Encrypt 會驗證失敗。

### 3. Docker / docker compose 已裝

```bash
docker --version           # ≥ 20.10
docker compose version     # ≥ 2.0
```

---

## 二、部署步驟

### Step 1 — 拉最新 code

```bash
cd /path/to/LIMS                 # 或第一次 clone
git pull origin main
```

### Step 2 — 建立 .env

```bash
cp .env.example .env
nano .env                        # 或你習慣的編輯器
```

**至少必須填的欄位**:

| 變數 | 怎麼產 |
|---|---|
| `DJANGO_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DB_PASSWORD` | 自訂強密碼,16+ 字元 |
| `MYSQL_ROOT_PASSWORD` | 跟 `DB_PASSWORD` 不同的強密碼 |
| `LIMS_ADMIN_PASSWORD` | LIMS admin 帳號的初始密碼 (≥12 字元) |
| `ADMIN_EMAIL` | Let's Encrypt 通知信箱(填能收信的) |

剩下保持預設即可。

### Step 3 — 停掉舊的 HTTP-only stack(若有在跑)

```bash
docker compose down
```

(volumes 不會被刪,資料庫資料安全保留)

### Step 4 — 起 HTTPS stack

```bash
docker compose --env-file .env up -d --build
```

**首次啟動需要 30~60 秒**,因為:
- Caddy 向 Let's Encrypt 申請憑證(用 HTTP-01 challenge,需要 80 通暢)
- Django 跑 `migrate`(包含自動建立 admin 帳號的 migration)
- MySQL 第一次初始化資料庫

### Step 5 — 驗證

```bash
# 1. 檢查容器狀態
docker compose ps
# 全部應該是 Up / healthy

# 2. 檢查 Caddy 拿到憑證
docker compose logs frontend | grep -E "certificate obtained|trying to solve"
# 看到 "certificate obtained" 就是成功

# 3. 從伺服器 curl
curl -I https://lims.ddns.net
# 應該回 HTTP/2 200,而且 SSL handshake 成功

# 4. 從瀏覽器
# 開 https://lims.ddns.net 應該看到登入頁,網址列出現綠色鎖
```

### Step 6 — 第一次登入

| 帳號 | 密碼 |
|---|---|
| `admin` | `.env` 裡填的 `LIMS_ADMIN_PASSWORD`(預設 `Admin@LIMS_2026!Sup`) |

第一次登入後立刻去 **管理後台 → 使用者 → 找到 admin → 編輯 → 更新密碼**。

---

## 三、運維日常

### 看 log

```bash
# 所有服務
docker compose logs -f

# 只看後端
docker compose logs -f backend

# 只看 Caddy(TLS / HTTP 訪問記錄)
docker compose logs -f frontend
```

### 重啟服務

```bash
# 例如 Django code 改了,只重 build backend
docker compose --env-file .env up -d --build backend

# 全部重啟
docker compose --env-file .env up -d
```

### 備份 MySQL

```bash
# 匯出
docker compose exec mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" lab_booking > backup-$(date +%F).sql

# 還原
docker compose exec -T mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" lab_booking < backup-2026-05-04.sql
```

### 憑證自動續期

Caddy **不需要任何手動操作**;它會在憑證到期前 30 天自動向 Let's Encrypt 換新。
要驗證:

```bash
docker compose exec frontend caddy list-modules | grep tls
# 看到 tls.* modules 都載入即可
```

`caddy_data` volume 持久化所有憑證 + ACME 帳號狀態,**不要刪它**。

---

## 四、疑難排解

### 1. `https://lims.ddns.net` 拿不到憑證 / Caddy log 說 "no such host"

DNS 沒指對。`dig lims.ddns.net` 應該回伺服器公網 IP。
DDNS 客戶端可能掛了,登入 DDNS provider 確認當前 IP。

### 2. Caddy log 說 "connection refused" / "i/o timeout"

防火牆 / NAT 沒開 80 + 443。確認:
- `ufw status` 沒擋
- 路由器 port forward 規則對(80→host, 443→host)
- ISP 有沒有擋 80(很多家用網路會)

### 3. 瀏覽器顯示「您的連線並非私人連線」

通常是 DNS 還沒生效或憑證沒拿到。等 5 分鐘 + `docker compose logs frontend` 看詳情。

### 4. 後端 502 Bad Gateway

```bash
docker compose logs backend
# 常見:DJANGO_SECRET_KEY 沒設、DB 還沒 ready
```

### 5. 帳號密碼忘了

```bash
docker compose exec backend python manage.py ensure_admin --password 'NewPass2026!'
```

### 6. 想暫時 rollback 回 HTTP

```bash
git checkout HEAD~1 -- docker-compose.yml frontend/Dockerfile frontend/Caddyfile
docker compose --env-file .env up -d --build
```

---

## 五、安全 / 合規檢查

部署完應該確認的事項:

- [ ] `https://lims.ddns.net` 拿到綠鎖,證書 valid
- [ ] `http://lims.ddns.net` 自動 301 redirect 到 HTTPS
- [ ] `https://lims.ddns.net` 回應 header 含 `Strict-Transport-Security`
- [ ] `https://lims.ddns.net` 回應 header 含 `X-Frame-Options: DENY`
- [ ] 已用新密碼登入,修掉預設 admin 密碼
- [ ] `.env` 檔在 host 機器權限 600(`chmod 600 .env`)
- [ ] MySQL port 3306 沒對外開(`docker compose ps mysql` 不該有 host 端口映射)
- [ ] 用 [SSL Labs](https://www.ssllabs.com/ssltest/analyze.html?d=lims.ddns.net) 跑 SSL 測試,目標分數 A+

---

## 六、架構簡圖

```
   [internet]
        │
        ▼
  ┌──────────────┐  Let's Encrypt (HTTPS auto-renewal)
  │  Caddy       │
  │  :443  :80   │ ──── HSTS / X-Frame-Options / gzip
  │              │
  │  路由規則:    │
  │   /api/*  ───┼──> backend:8000  (Django + gunicorn)
  │   /admin/* ─┐│      │
  │   /  → SPA │└──────┼──> mysql:3306
  └────────────┴───────┴──> redis:6379
  Volumes:
    caddy_data    (Let's Encrypt cert)
    mysql_data    (DB persisted)
```

---

## 附錄:環境變數速查

| 變數 | 用途 | 範例 |
|---|---|---|
| `DJANGO_SECRET_KEY` | session/JWT 簽名 | `secrets.token_urlsafe(50)` 產出 |
| `DJANGO_ALLOWED_HOSTS` | Django 接受的 Host header | `lims.ddns.net,www.lims.ddns.net` |
| `CORS_ALLOWED_ORIGINS` | 允許的瀏覽器 origin | `https://lims.ddns.net` |
| `LIMS_ADMIN_PASSWORD` | 預設 admin 密碼 | 16+ chars |
| `DB_PASSWORD` | MySQL `lab_user` 密碼 | 16+ chars |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密碼 | 跟上面不同 |
| `ADMIN_EMAIL` | Let's Encrypt 通知 | 真實能收信的 mailbox |
| `SENTRY_DSN` | Sentry 錯誤追蹤 | (可選) |

`.env` 完整範本見 [`.env.example`](../.env.example)。
