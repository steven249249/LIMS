# LIMS Backend (Django 5.2 + DRF)

Server-side of the LIMS relay management system. Built around six focused
Django apps, with a state-machine service layer for orders, an audit-trail
middleware that captures every authenticated request, a hardened settings
profile for production, and a 91-test pytest suite that demonstrates the
AAA pattern alongside all five canonical test-double styles.

> If you arrived here looking for the project overview, see the
> [root README](../README.md).

---

## Table of contents

- [App map](#app-map)
- [Domain model](#domain-model)
- [Order state machine](#order-state-machine)
- [Visibility scoping](#visibility-scoping)
- [API surface](#api-surface)
- [Setup](#setup)
- [Configuration / environment](#configuration--environment)
- [Custom management commands](#custom-management-commands)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Common tasks](#common-tasks)

---

## App map

| App | Purpose | Key models |
|---|---|---|
| **users** | Identity and organisational hierarchy | `FAB`, `Department`, `User` (custom UUID PK + `role` choice) |
| **equipments** | Equipment catalogue and experiment requirements | `Experiment`, `EquipmentType`, `Equipment`, `ExperimentRequiredEquipment` |
| **orders** | Sample submission, relay flow, state machine | `Order`, `OrderStage` (+ `services.py`) |
| **scheduling** | Equipment-time bookings with conflict detection | `EquipmentBooking` (+ `services.py` using `select_for_update`) |
| **monitoring** | Activity log + dashboard stats + middleware | `ActivityLog`, `ActivityLogMiddleware`, `IsSystemSuperuser` |
| **admin_api** | Superuser-only ModelViewSets (CRUD over 10 tables) | re-uses the above; defines admin-shaped serializers |

Cross-cutting `utils/` package: a `RequestIDMiddleware` plus a
`custom_exception_handler` that wraps every API error in a uniform envelope.

---

## Domain model

```
            ┌─────────┐ 1     N ┌────────────┐ 1     N ┌──────┐
            │   FAB   │────────►│ Department │────────►│ User │
            └─────────┘         └─────┬──────┘         └──┬───┘
                                      │                   │
                                      │                   │
            ┌──────────────┐         │                   │
            │ EquipmentType│         │                   │
            └──────┬───────┘         │                   │
                   │ 1               │ 1                 │
                   │                 │                   │ submitter
                   ▼ N               ▼ N                 ▼
            ┌──────────────┐  ┌──────────────────┐  ┌────────┐
            │  Equipment   │  │  ExperimentReq.  │  │  Order │
            └──────┬───────┘  │  (M:N + step)    │  └────┬───┘
                   │          └─────┬────────────┘       │ 1
                   │                │                    │
                   │ 1              │ N                  │ N
                   │                ▼                    ▼
                   │          ┌─────────────┐      ┌────────────┐
                   │          │ Experiment  │      │ OrderStage │
                   │          └─────────────┘      └─────┬──────┘
                   │                                     │
                   ▼                                     │
            ┌──────────────────┐ N             1         │
            │ EquipmentBooking │◄───────────────────────┘
            └──────────────────┘
```

All primary keys are UUIDs.

---

## Order state machine

`orders/services.py` encapsulates the lifecycle:

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

`OrderStage` rides the same machine independently:

- `pending` → waits for previous stage to finish
- `waiting` → ready, manager must approve + schedule
- `in_progress` → assignee may complete after `schedule_start`
- `done` → relays to the next stage; if last, marks the order `done`
- `rejected` → rejection cascades to the order

Allowed transitions are enforced by `_TRANSITIONS` and `_assert_transition`
in `orders/services.py`. Tests freeze time with `freezegun.freeze_time(...)`
to verify the time-locked completion guard.

---

## Visibility scoping

Every list / detail endpoint enforces row-level filtering based on
`request.user.role`:

| Role | Orders visible | Stages visible |
|---|---|---|
| `regular_employee` | Orders they submitted | Stages on those orders |
| `lab_member` | Orders that have a stage assigned to them | Only stages assigned to them |
| `lab_manager` | Orders in their department | All stages in their department |
| `superuser` | Everything | Everything |

Out-of-scope reads return **404, not 403** — see `OrderDetailView.get_queryset`
in `orders/views.py`. Coverage:
`backend/tests/test_visibility_scoping.py` (13 tests).

---

## API surface

| Prefix | Module | Endpoints |
|---|---|---|
| `/api/users/` | `users.urls` | `login` (JWT), `token/refresh`, `register`, `profile`, `fabs`, `departments`, `<list>` |
| `/api/orders/` | `orders.urls` | `<list>` / `<detail>` / `create` / `stages/` / `stages/<id>/review` / `stages/<id>/complete` |
| `/api/equipments/` | `equipments.urls` | `experiments/`, `equipment-types/`, `equipment/`, `status-matrix/`, `capacity-check/` |
| `/api/scheduling/` | `scheduling.urls` | `bookings/`, `availability-check/` |
| `/api/monitoring/` | `monitoring.urls` | `dashboard/` (stats), `logs/` (audit, paginated + filtered) |
| `/api/admin/` | `admin_api.urls` | 10 `DefaultRouter` ViewSets — fabs, departments, users, experiments, equipment-types, equipment, experiment-requirements, orders, order-stages, bookings |

All routes require JWT (`Bearer …`) except `/api/users/login/`,
`/api/users/register/`, and `/api/users/token/refresh/`.

---

## Setup

```bash
cd backend
python -m venv ../venv
source ../venv/bin/activate          # Windows: ..\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata seed_data.json
python manage.py ensure_admin
python manage.py runserver
```

The API listens on `http://127.0.0.1:8000`.

---

## Configuration / environment

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Set to `False` for production |
| `DJANGO_PRODUCTION` | `False` | When `True`: refuses dev secret + wildcard hosts; enables HSTS, SSL redirect, secure cookies |
| `DJANGO_SECRET_KEY` | dev fallback | Required when `DJANGO_PRODUCTION=True` |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated |
| `DB_ENGINE` | (sqlite) | `mysql` to switch backends |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | — | MySQL only |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Cache + Celery broker |
| `CORS_ALLOWED_ORIGINS` | dev frontends | Comma-separated origins |
| `SENTRY_DSN` | empty | Enable when present; otherwise inert |
| `LIMS_ADMIN_PASSWORD` | `Admin@LIMS_2026!Sup` | Used by `ensure_admin` |
| `DJANGO_LOG_LEVEL` | `INFO` | Stdlib logging level |

`CORS_ALLOW_ALL_ORIGINS` is **never** enabled — wildcard CORS is intentionally
not supported.

---

## Custom management commands

| Command | What it does |
|---|---|
| `python manage.py ensure_admin [--username admin] [--password ...]` | Idempotently creates / refreshes the system superuser. Reads `LIMS_ADMIN_PASSWORD` env var when no flag is given. |
| `python manage.py loaddata seed_data.json` | Bootstraps FABs, Departments, Experiments, EquipmentTypes, Equipment, ExperimentRequiredEquipment, and 8 demo users (passwords already hashed). |
| `python manage.py dumpdata users equipments --indent=2` | Re-export seed data after editing locally. |

---

## Testing

```bash
unset PYTHONPATH                        # avoid ROS humble's broken pytest plugin (Linux)
pytest
```

Output (current):

```
======================== 91 passed in 17 s ========================
```

### Test coverage of new modules

| Module | Coverage |
|---|---|
| `utils/request_id.py` | **100 %** |
| `utils/exception_handler.py` | **96 %** |
| `monitoring/middleware.py` | **95 %** |
| `admin_api/views.py` | **99 %** |
| `monitoring/views.py` | **88 %** |

### Test files

| File | What it covers |
|---|---|
| `tests/test_monitoring_middleware.py` | `_redact`, `_classify`, `_client_ip`, persistence semantics |
| `tests/test_request_id.py` | UUID generation, header pass-through, length cap |
| `tests/test_exception_handler.py` | Uniform error envelope per exception type, traceback masking |
| `tests/test_orders_services.py` | Order / stage state-machine + the five test-double styles |
| `tests/test_admin_api_integration.py` | Permission matrix + CRUD over 10 admin resources |
| `tests/test_monitoring_api_integration.py` | Dashboard + paginated activity log filtering |
| `tests/test_auth_integration.py` | JWT login / refresh / profile + uniform error shape |
| `tests/test_visibility_scoping.py` | Row-level visibility for every role |

### Five test-double styles (showcased in `test_orders_services.py`)

| Style | Where |
|---|---|
| **Fake** (full ORM) | `factory_boy` factories under `tests/factories.py` |
| **Stub** (canned input) | conftest fixtures (`employee`, `lab_manager`, …) |
| **Mock** (replace + verify) | `mocker.patch('scheduling.services.allocate_equipments_for_stage', return_value=[])` |
| **Spy** (observe without replacing) | `mocker.spy(services, '_send_notification')` |
| **Time fake** | `freezegun.freeze_time('2026-05-01 10:00:00')` |

### Pytest fixtures (in `conftest.py`)

| Fixture | Returns |
|---|---|
| `employee`, `lab_manager`, `lab_member`, `superuser` | A `User` of that role (with department and department→fab attached) |
| `employee_client`, `manager_client`, `member_client`, `superuser_client` | A pre-authenticated `APIClient` for each role |
| `equipment_type`, `equipment`, `experiment`, `order`, `order_stage` | Domain objects via `factory_boy` |
| `api_client` | Anonymous `APIClient` |

---

## Project layout

```
backend/
├── backend/                # project conf
│   ├── settings.py         # env-driven, prod-aware
│   └── urls.py             # /api/<app>/
│
├── users/
│   ├── models.py           # FAB, Department, User (UUID + role)
│   ├── serializers.py
│   ├── views.py            # register, profile, list, JWT login (delegated)
│   └── migrations/
│
├── orders/
│   ├── models.py           # Order, OrderStage
│   ├── services.py         # create_order, approve_and_schedule_stage, complete_stage,
│   │                       # reject_order — enforces transitions + notifications
│   ├── serializers.py
│   ├── views.py            # OrderListView, OrderDetailView (with visibility scoping),
│   │                       # OrderReviewView, OrderStageListView, OrderCompleteView
│   └── migrations/
│
├── equipments/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py            # status-matrix, capacity-check
│   └── migrations/
│
├── scheduling/
│   ├── models.py           # EquipmentBooking
│   ├── services.py         # allocate_equipments_for_stage (select_for_update)
│   ├── views.py            # availability-check
│   └── migrations/
│
├── monitoring/
│   ├── models.py           # ActivityLog (+ 3 indexes)
│   ├── middleware.py       # ActivityLogMiddleware (redacts password/token, 8KB body cap)
│   ├── permissions.py      # IsSystemSuperuser (role-based, not Django's is_superuser)
│   ├── serializers.py
│   ├── views.py            # DashboardStatsView, ActivityLogListView
│   ├── urls.py
│   ├── admin.py            # read-only Django admin
│   └── management/
│       └── commands/
│           └── ensure_admin.py
│
├── admin_api/
│   ├── serializers.py      # 10 admin-shaped serializers (denormalised labels for tables)
│   ├── views.py            # 10 ModelViewSets gated by IsSystemSuperuser
│   └── urls.py             # DefaultRouter
│
├── utils/
│   ├── request_id.py       # X-Request-ID middleware
│   └── exception_handler.py # uniform DRF error envelope + 5xx masking
│
├── tests/
│   ├── conftest.py         # role-based fixtures + pre-authed clients
│   ├── factories.py        # factory_boy factories for every model
│   └── test_*.py           # 91 cases across 8 files
│
├── pytest.ini
├── requirements.txt
└── manage.py
```

---

## Common tasks

### Add a new domain model

1. Define the model in the relevant app (`<app>/models.py`).
2. `python manage.py makemigrations <app>` and inspect the migration before committing.
3. Decide whether the superuser console should manage it. If yes:
   - Add a serializer in `admin_api/serializers.py` (denormalise labels for the table view).
   - Register a `ModelViewSet` in `admin_api/views.py` and route it in `admin_api/urls.py`.
4. Add a factory in `tests/factories.py`.
5. Cover the new behaviour with an integration test.

### Promote a regular user to superuser

```bash
python manage.py shell -c "from users.models import User; u = User.objects.get(username='alice'); u.role = 'superuser'; u.is_staff = True; u.is_superuser = True; u.save()"
```

### Reset to seed-only state

```bash
rm db.sqlite3
python manage.py migrate
python manage.py loaddata seed_data.json
python manage.py ensure_admin
```

### Add a new role-scoped endpoint

1. Build the queryset in `<app>/views.py`. Use `request.user.role` and filter
   accordingly. Out-of-scope reads should return 404 via queryset filtering,
   not 403 — keeps existence opaque.
2. Add visibility tests under `tests/test_visibility_scoping.py` covering all
   four roles.

### Tail the audit trail in dev

```python
python manage.py shell -c "from monitoring.models import ActivityLog; [print(l) for l in ActivityLog.objects.order_by('-timestamp')[:20]]"
```
