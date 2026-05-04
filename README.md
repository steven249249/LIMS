# LIMS — Semiconductor FAB Relay Management System

[![CI](https://github.com/asddzxcc1856/LIMS/actions/workflows/ci.yml/badge.svg)](https://github.com/asddzxcc1856/LIMS/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Django](https://img.shields.io/badge/django-5.2-success)
![Vue](https://img.shields.io/badge/vue-3.5-brightgreen)
![Tests](https://img.shields.io/badge/tests-91%20pytest%20%2B%2039%20vitest%20%2B%208%20e2e-success)
![License](https://img.shields.io/badge/license-MIT-blue)

A laboratory information management system tailored for semiconductor FAB
environments, built around a multi-stage **relay workflow** that walks each
sample through specialised laboratories — Photo, Process, QC — with strict
role-based access control, real-time equipment timeline awareness, and a
full-blown superuser admin console for system operators.

---

## Table of contents

- [Highlights](#-highlights)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Technology stack](#-technology-stack)
- [Quick start](#-quick-start)
- [Demo accounts](#-demo-accounts)
- [Role matrix](#-role-matrix)
- [Project layout](#-project-layout)
- [Testing](#-testing)
- [CI / CD](#-ci--cd)
- [Configuration](#-configuration)
- [Subsystem docs](#-subsystem-docs)
- [License](#-license)

---

## ✨ Highlights

| Feature | Detail |
|---|---|
| **Relay workflow** | Each `Order` is auto-decomposed into ordered `OrderStage` records driven by `ExperimentRequiredEquipment.step_order`. Completing a stage releases the next lab's queue. |
| **Role-based visibility** | Row-level scoping per role: requesters see only their own orders, lab members see only their own assigned stages, lab managers see only their lab, superusers see everything. Out-of-scope reads return 404 (not 403) to avoid existence leaks. |
| **Interactive equipment timeline** | 72px high-density rows with glassmorphism aesthetics. Bookings can be edited inline; conflict detection is enforced server-side via `select_for_update`. |
| **Time-locked completion** | A lab member cannot mark a stage done before its scheduled start time — keeps SOP compliance. |
| **Admin console** | Superuser-only `/admin/*` UI: live KPI dashboard, audit log with filter/drawer, full CRUD over every domain table (10 resources). |
| **Audit trail (everything)** | Every authenticated request is persisted to `ActivityLog` with redacted body, IP, status, duration. Correlated with `X-Request-ID` for trace stitching. |
| **Hardened by default** | Production profile (`DJANGO_PRODUCTION=True`) refuses dev secret/wildcard hosts, enables HSTS, secure cookies, content-type nosniff, X-Frame-Options=DENY. |
| **i18n + light/dark theme** | Per-user language (zh-TW / English) and theme (light / dark) preferences, persisted in localStorage, applied without reload. |

---

## 📸 Screenshots

| | |
|---|---|
| Login | ![login screen](docs/screenshots/login.png) |
| Dashboard | ![dashboard](docs/screenshots/dashboard.png) |
| Equipment Timeline | ![timeline](docs/screenshots/timeline.png) |
| Admin Console | ![admin](docs/screenshots/admin-dashboard.png) |

> Add the actual PNG files under `docs/screenshots/` when ready — placeholders kept so the README renders.

---

## 🏗 Architecture

```
                      ┌───────────────────────────────────────┐
                      │           Browser (Vue 3)             │
                      │  ant-design-vue · Pinia · vue-router  │
                      │  vue-i18n (zh-TW / en) · light/dark   │
                      └───────────┬───────────────────────────┘
                                  │ JSON over HTTPS · JWT Bearer
                                  │ X-Request-ID round-trips
                                  ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                          Django 5.2 + DRF                             │
   │                                                                        │
   │  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────┐  │
   │  │  users   │  │  orders  │  │ equipments │  │scheduling│  │admin_│  │
   │  │  /auth   │  │ /relay   │  │ /catalog   │  │ /booking │  │  api │  │
   │  └────┬─────┘  └────┬─────┘  └────┬───────┘  └────┬─────┘  └──┬───┘  │
   │       │             │             │                │            │     │
   │       └─────────────┴─────────────┴────────────────┴────────────┘     │
   │                                  │                                     │
   │       ┌──────────────────────────┴──────────────────────────┐          │
   │       │  monitoring · ActivityLog (audit) · DashboardStats   │         │
   │       │  utils · request_id middleware · custom exception    │         │
   │       └──────────────────────────────────────────────────────┘          │
   │                                  │                                     │
   └──────────────────────────────────┼─────────────────────────────────────┘
                                      ▼
                       ┌──────────────────────────┐
                       │  SQLite (dev) / MySQL    │
                       │  Redis (cache, optional) │
                       │  Sentry (errors, opt)    │
                       └──────────────────────────┘
```

**Order state machine**

```
              create_order()
   ┌────────┐    ──────►     ┌─────────┐  approve   ┌────────────┐  complete   ┌──────┐
   │Created │                │ Waiting │ ─────────► │In Progress │ ──────────► │ Done │
   └────────┘                └─────┬───┘            └────────────┘             └──────┘
                                   │ reject
                                   ▼
                              ┌──────────┐
                              │ Rejected │
                              └──────────┘
```

Each `OrderStage` walks the same machine independently; completion of stage *N*
moves stage *N+1* from `pending` to `waiting` and notifies its lab manager.

---

## 🛠 Technology stack

### Backend

| Layer | Choice |
|---|---|
| Framework | Django 5.2 + Django REST Framework |
| Auth | JWT via `djangorestframework-simplejwt` (2h access, 7d refresh) |
| Database | SQLite (dev) / MySQL 8 (production) |
| Caching | Redis 7 (optional, for throttling and Celery) |
| Background jobs | Celery 5.6 (broker pre-wired, no critical path uses it yet) |
| Observability | Structured logging via stdlib + Sentry SDK (opt-in via `SENTRY_DSN`) |
| Testing | pytest + pytest-django + factory-boy + freezegun + pytest-mock |

### Frontend

| Layer | Choice |
|---|---|
| Framework | Vue 3 (Composition API + `<script setup>`) |
| State | Pinia 3 |
| Router | Vue Router 4 (role-based guards) |
| UI library | Ant Design Vue 4 (`@ant-design/icons-vue`) |
| Build | Vite 8 |
| HTTP | Axios with JWT interceptor + automatic refresh-on-401 |
| i18n | vue-i18n 9 (Composition API mode) |
| Date | dayjs |
| Testing | Vitest 3 + @vue/test-utils + jsdom + Playwright |

### Operations

| Layer | Choice |
|---|---|
| CI | GitHub Actions (`.github/workflows/ci.yml`) — backend pytest + frontend vitest + frontend build + Playwright e2e |
| CD | GitHub Actions draft (`.github/workflows/cd.yml`) — Cloud Run via Workload Identity Federation. **Disabled** until target GCP project is provisioned. |
| Containers | `Dockerfile` for backend and frontend; `docker-compose.yml` for local stack |
| Secrets | All sensitive values flow from environment variables; never committed |

---

## 🚀 Quick start

### Prerequisites

- Python 3.10+
- Node.js 20+ (Node 25 supported with the polyfill in `frontend/tests/setup.js`)
- Git

### 1. Clone and provision

```bash
git clone https://github.com/asddzxcc1856/LIMS.git
cd LIMS
```

### 2. Backend

```bash
cd backend
python -m venv ../venv
source ../venv/bin/activate          # Windows: ..\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata seed_data.json   # FABs, departments, experiments, demo users
python manage.py ensure_admin              # creates / refreshes admin password
python manage.py runserver
```

The API is now serving at `http://127.0.0.1:8000`.

### 3. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in a browser.

> **System ROS users**: if pytest is dragging in a broken `launch_testing` plugin, run with `unset PYTHONPATH && pytest`. The `frontend/tests/setup.js` already polyfills the broken `localStorage` shipping with Node 25.

---

## 🔐 Demo accounts

Loaded by `python manage.py loaddata seed_data.json` and `ensure_admin`:

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@LIMS_2026!Sup` | Superuser (full system access + admin console) |
| `Lab_Mgr_Photo_001` | (set during seed dump) | Lab manager — Photo |
| `Lab_Mgr_Process_001` | (set during seed dump) | Lab manager — Process |
| `Lab_Mgr_QC_001` | (set during seed dump) | Lab manager — QC |
| `Lab_Mem_Photo_001` | (set during seed dump) | Lab member — Photo |
| `Lab_Mem_Process_001` | (set during seed dump) | Lab member — Process |
| `Lab_Mem_QC_001` | (set during seed dump) | Lab member — QC |
| `testuser` | `testpass` | Regular employee (sample requester) |

> Demo passwords for non-admin accounts are inherited from the seed fixture. Reset any of them via `python manage.py changepassword <username>` before going live.

---

## 👥 Role matrix

| Capability | Requester | Lab Member | Lab Manager | Superuser |
|---|:---:|:---:|:---:|:---:|
| Submit a sample order | ✅ own | — | — | ✅ |
| View own orders | ✅ | — | — | ✅ |
| View dept-scoped orders | — | — | ✅ | ✅ |
| View ALL orders | — | — | — | ✅ |
| Execute assigned stage | — | ✅ self | ✅ dept | ✅ |
| Approve / reject / re-assign stages | — | — | ✅ dept | ✅ |
| Edit equipment booking timeline | — | — | ✅ dept | ✅ |
| Allocate equipment to a lab (CRUD) | — | — | — | ✅ admin |
| View activity log / dashboard stats | — | — | — | ✅ admin |
| CRUD any domain table | — | — | — | ✅ admin |

> The "view" rules are enforced **at row level on the API** — out-of-scope reads return 404 rather than 403 to avoid leaking existence.

---

## 📁 Project layout

```
LIMS/
├── backend/                    # Django project — see backend/README.md
│   ├── backend/                #   project settings + URL conf
│   ├── users/                  #   FAB / Department / User (custom UUID PK)
│   ├── orders/                 #   Order / OrderStage + state-machine services
│   ├── equipments/             #   Experiment / EquipmentType / Equipment / requirements
│   ├── scheduling/             #   EquipmentBooking + select_for_update conflict guard
│   ├── monitoring/             #   ActivityLog model + middleware + dashboard API
│   ├── admin_api/              #   Superuser-only ModelViewSets (CRUD over 10 models)
│   ├── utils/                  #   request_id middleware + custom DRF exception handler
│   ├── tests/                  #   91 pytest cases (factories, AAA, 5 test-double styles)
│   ├── conftest.py             #   shared fixtures incl. per-role authenticated APIClient
│   ├── pytest.ini              #   pytest config
│   ├── seed_data.json          #   FABs + Departments + Experiments + demo Users
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/                   # Vue 3 SPA — see frontend/README.md
│   ├── src/
│   │   ├── api/                #   axios instance + per-domain modules + admin.js wrapper
│   │   ├── stores/             #   auth (JWT) + settings (locale + theme)
│   │   ├── router/             #   role-aware guards
│   │   ├── i18n/               #   zh-TW + en catalogues
│   │   ├── views/
│   │   │   ├── admin/          #     12 admin pages — dashboard, logs, 10 CRUD pages
│   │   │   ├── requester/      #     OrderList / OrderCreate
│   │   │   ├── manager/        #     OrderReview (timeline + 4 modals)
│   │   │   └── member/         #     OrderTasks (time-locked completion)
│   │   ├── components/admin/   #   Generic CrudTable shared by 10 admin pages
│   │   ├── App.vue             #   Layout shell + ConfigProvider + Settings drawer
│   │   └── main.js
│   ├── tests/                  # 39 vitest cases (stores, api, components)
│   ├── e2e/                    # 8 Playwright specs (login, admin console, CRUD)
│   ├── playwright.config.js
│   └── vite.config.js
│
├── .github/workflows/
│   ├── ci.yml                  # backend pytest + frontend vitest + build + e2e
│   └── cd.yml                  # GCP Cloud Run deploy — DRAFT, disabled
└── docker-compose.yml          # local backend + frontend orchestration
```

---

## ✅ Testing

| Suite | Tool | Count | Run |
|---|---|---:|---|
| Backend unit + integration | pytest + factory-boy + freezegun | 91 | `cd backend && pytest` |
| Frontend unit + component | vitest + @vue/test-utils | 39 | `cd frontend && npm test` |
| End-to-end | Playwright (chromium) | 8 | `cd frontend && npm run e2e` |

Backend tests follow Arrange / Act / Assert and demonstrate the five canonical
**test-double** styles (Fake / Stub / Mock / Spy / Time-fake) — see
`backend/tests/test_orders_services.py` for examples.

Frontend tests live alongside their unit; `tests/setup.js` polyfills
`localStorage` because Node 25 ships an experimental built-in whose Web Storage
methods are missing.

E2E tests need both servers running. Use:

```bash
# Terminal 1 — backend
cd backend && python manage.py runserver
# Terminal 2 — frontend e2e (auto-starts vite via webServer config)
cd frontend && npm run e2e
```

---

## 🤖 CI / CD

`.github/workflows/ci.yml` runs on every push and PR to `main`:

| Job | Steps |
|---|---|
| **backend** | install deps → run `pytest` → upload coverage |
| **frontend-unit** | `npm ci` → `npm test` (vitest) → `npm run build` |
| **e2e** | boot Django (load seed + `ensure_admin`) → `npx playwright test` → upload report on failure |

Concurrency group cancels in-progress runs on rapid pushes.

`.github/workflows/cd.yml` is a **disabled draft** that builds container images,
pushes to Artifact Registry, and rolls them out to Cloud Run via Workload
Identity Federation. The workflow file documents the four-step enable
procedure inline.

---

## ⚙️ Configuration

All environment variables read by Django:

| Var | Default | Description |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Set to `False` for production |
| `DJANGO_PRODUCTION` | `False` | When `True`, refuses dev secret + wildcard hosts, enables HSTS / SSL redirect / Secure cookies |
| `DJANGO_SECRET_KEY` | dev fallback | Required when `DJANGO_PRODUCTION=True` |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated host list |
| `DB_ENGINE` | (sqlite) | Set to `mysql` to switch to MySQL |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | MySQL credentials |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | For caching / Celery broker |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated |
| `SENTRY_DSN` | (empty) | Set to enable Sentry error tracking |
| `LIMS_ADMIN_PASSWORD` | `Admin@LIMS_2026!Sup` | Used by `python manage.py ensure_admin` |

Frontend (Vite):

| Var | Default | Description |
|---|---|---|
| `VITE_API_BASE` | `http://127.0.0.1:8000/api` | Override to point at a deployed backend |

---

## 📚 Subsystem docs

- [backend/README.md](backend/README.md) — Django app structure, models, services, testing patterns
- [frontend/README.md](frontend/README.md) — Vue project layout, theming, i18n, admin console internals

---

## 📝 License

Distributed under the MIT License.

---

*Built with care for semiconductor FAB excellence.*
