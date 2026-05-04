# LIMS Frontend (Vue 3 + Vite)

Single-page application for the LIMS relay management system. Built on Vue 3
(Composition API + `<script setup>`), styled end-to-end with **ant-design-vue**,
state managed with Pinia, navigation guarded by Vue Router, and internationalised
to Traditional Chinese (default) + English with a runtime light/dark theme switch.

> Looking for the project overview? See the [root README](../README.md).
> The Django backend is documented in [`../backend/README.md`](../backend/README.md).

---

## Table of contents

- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Setup](#setup)
- [Development](#development)
- [Testing](#testing)
- [Theming and i18n](#theming-and-i18n)
- [Admin console internals](#admin-console-internals)
- [Routing and role guards](#routing-and-role-guards)
- [API client](#api-client)
- [Common tasks](#common-tasks)

---

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | Vue 3.5 | Composition API + `<script setup>` everywhere |
| Build | Vite 8 | `vite.config.js` left intentionally minimal |
| State | Pinia 3 | `auth` store + `settings` store (locale + theme) |
| Router | Vue Router 4 | Role-aware guards via `meta.roles` |
| UI library | ant-design-vue 4 | `<a-config-provider>` powers theme + locale switching |
| Icons | `@ant-design/icons-vue` | Tree-shaken |
| HTTP | axios | JWT interceptor + automatic refresh-on-401 in `api/client.js` |
| i18n | vue-i18n 9 | Composition API mode (`legacy: false`) |
| Date | dayjs | Used by every date-picker / formatter |
| Unit / component testing | vitest 3 + @vue/test-utils + jsdom | `npm test` |
| End-to-end | Playwright (chromium) | `npm run e2e` |

---

## Project layout

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js          # axios instance + JWT interceptor + refresh-on-401
│   │   ├── users.js           # /api/users/*
│   │   ├── orders.js          # /api/orders/*
│   │   ├── equipments.js      # /api/equipments/*
│   │   ├── scheduling.js      # /api/scheduling/*
│   │   └── admin.js           # uniform CRUD wrappers for /api/admin/* + dashboard/log
│   │
│   ├── stores/
│   │   ├── auth.js            # JWT + user profile + role computeds
│   │   └── settings.js        # locale + theme + persistence
│   │
│   ├── router/
│   │   └── index.js           # routes + role-aware navigation guard
│   │
│   ├── i18n/
│   │   ├── index.js           # createI18n, reads persisted locale
│   │   ├── zh-TW.js           # Traditional Chinese catalogue
│   │   └── en.js              # English catalogue
│   │
│   ├── views/
│   │   ├── LoginView.vue      # gradient brand card, antd Form rules
│   │   ├── RegisterView.vue
│   │   ├── DashboardView.vue  # KPI statistics + quick-action panel
│   │   ├── EquipmentDashboardView.vue   # filterable equipment grid
│   │   │
│   │   ├── requester/
│   │   │   ├── OrderListView.vue        # antd Table + relay Steps drawer
│   │   │   └── OrderCreateView.vue      # antd Form + capacity preview
│   │   │
│   │   ├── manager/
│   │   │   └── OrderReviewView.vue      # 4 modals: approve / reject / reassign / booking
│   │   │
│   │   ├── member/
│   │   │   └── OrderTasksView.vue       # time-locked complete via Popconfirm
│   │   │
│   │   └── admin/
│   │       ├── AdminLayout.vue          # /admin shell — collapsible dark sider
│   │       ├── DashboardView.vue        # KPI cards + 30 s auto-refresh
│   │       ├── ActivityLogsView.vue     # 6 filters + detail Drawer
│   │       ├── FabsView.vue             # 10 CRUD pages
│   │       ├── DepartmentsView.vue
│   │       ├── UsersView.vue
│   │       ├── ExperimentsView.vue
│   │       ├── EquipmentTypesView.vue
│   │       ├── EquipmentView.vue
│   │       ├── ExperimentRequirementsView.vue
│   │       ├── OrdersView.vue
│   │       ├── OrderStagesView.vue
│   │       └── BookingsView.vue
│   │
│   ├── components/
│   │   ├── TimelineChart.vue            # legacy 72px timeline (kept as-is)
│   │   └── admin/
│   │       └── CrudTable.vue            # generic CRUD component — drives all 10 admin pages
│   │
│   ├── App.vue                          # ConfigProvider + layout shell + Settings drawer
│   ├── main.js                          # plugins: pinia, router, i18n, antd
│   └── style.css                        # tokens + dark/light CSS variables
│
├── tests/                                # vitest unit / component tests
│   ├── setup.js                          # localStorage polyfill (Node 25 fix)
│   ├── auth.store.test.js                # 9 cases
│   ├── settings.store.test.js            # 9 cases
│   ├── admin.api.test.js                 # 9 cases
│   ├── LoginView.test.js                 # 4 cases
│   └── CrudTable.test.js                 # 8 cases
│
├── e2e/                                  # Playwright specs
│   ├── login.spec.js                     # 3 cases
│   ├── admin-console.spec.js             # 4 cases
│   └── admin-crud.spec.js                # 1 full create→edit→delete cycle
│
├── playwright.config.js
├── vitest.config.js
├── vite.config.js
└── package.json
```

---

## Setup

```bash
cd frontend
npm install
npm run dev     # http://127.0.0.1:5173
```

Backend must already be running on `http://127.0.0.1:8000`. Override with
`VITE_API_BASE` if pointing at a remote backend:

```bash
VITE_API_BASE=https://api.lims.example.com/api npm run dev
```

---

## Development

| Command | Effect |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview the production build |
| `npm test` | Run vitest once |
| `npm run test:watch` | Vitest in watch mode |
| `npm run test:coverage` | Vitest + v8 coverage report |
| `npm run e2e` | Playwright (auto-starts vite via webServer config) |
| `npm run e2e:ui` | Playwright UI mode |

The dev server proxies API calls to the backend baseURL configured in
`src/api/client.js`. CORS is whitelisted for `localhost:5173` and `127.0.0.1:5173`
on the Django side.

---

## Testing

### Unit / component (vitest)

5 files, **39 cases**. Run with `npm test`.

| File | Coverage focus |
|---|---|
| `auth.store.test.js` | Token persistence, logout cleanup, profile-load failure path, role computed matrix |
| `settings.store.test.js` | Defaults, persistence, unknown-value rejection, toggle helpers, `data-theme` DOM stamping |
| `admin.api.test.js` | Every CRUD verb of every admin resource + dashboard/log fetchers (axios stubbed) |
| `LoginView.test.js` | Form wiring + login flow + backend error message surfacing |
| `CrudTable.test.js` | Generic CRUD lifecycle: pagination, search reload, modal init, write-only password handling, delete reload |

The `tests/setup.js` polyfills `localStorage` because Node 25 ships an
experimental built-in whose Web Storage methods (`getItem`, `setItem`, `clear`,
…) are missing. jsdom 29 surfaces the same broken object on `window.localStorage`,
so production code that calls `localStorage.getItem(...)` would otherwise crash.

### End-to-end (Playwright)

3 files, **8 cases**. Run with `npm run e2e` (the backend must be available
on `:8000` first).

| File | Coverage |
|---|---|
| `login.spec.js` | Empty-form validation, bad-credential error envelope, admin happy path |
| `admin-console.spec.js` | Dashboard KPI cards, log filter UI, sidebar nav, non-superuser router guard |
| `admin-crud.spec.js` | Full lifecycle: create → search → edit → delete an `EquipmentType` via the UI |

Selectors absorb ant-design's CJK button-spacing quirk (`登入` → `登 入`)
through a regex helper. Page titles anchor on
`.ant-page-header-heading-title` to disambiguate from sidebar / breadcrumb.

---

## Theming and i18n

Both preferences live in `stores/settings.js`, persist to localStorage, and
apply instantly without reloading.

### How theme switching works

- `App.vue` wraps everything in `<a-config-provider :theme="...">`.
- `theme.algorithm` is bound to `darkAlgorithm` or `defaultAlgorithm` based
  on `useSettingsStore().isDark`. Every antd component switches automatically.
- `style.css` defines a dark-mode block under `:root[data-theme='dark']` for
  the legacy `--c-*` custom properties used by `TimelineChart`.
- The store stamps `data-theme="dark"` onto `<html>` so global CSS sees it.

### How language switching works

- `App.vue` binds `<a-config-provider :locale="...">` to either `zh_TW` or
  `en_US` from ant-design-vue's bundled locales — that swaps date pickers,
  pagination text, etc.
- A `watch` on `settings.locale` updates vue-i18n's active locale.
- vue-i18n catalogues live in `src/i18n/zh-TW.js` and `src/i18n/en.js`.

### Add a new locale string

1. Add the key under both `zh-TW.js` and `en.js`. Match the nesting style
   (`auth.login`, `dashboard.totalOrders`, …).
2. In a component:
   ```vue
   <script setup>
   import { useI18n } from 'vue-i18n'
   const { t } = useI18n()
   </script>

   <template>
     <a-button>{{ t('auth.login') }}</a-button>
   </template>
   ```
3. For interpolations: `t('dashboard.welcome', { name: user.username })`.

### What's already translated

- `App.vue` (sidebar, header, footer, user dropdown)
- `LoginView`, `RegisterView`
- Root `DashboardView`

Other pages still ship literal zh-TW strings — the i18n plumbing is in place,
they can be migrated incrementally without touching infrastructure.

---

## Admin console internals

`/admin/*` is a self-contained shell rendered by `views/admin/AdminLayout.vue`.
It bypasses the main app shell because the route guard in `router/index.js`
sets `meta.roles = ['superuser']`, and `App.vue` skips its own layout for
paths starting with `/admin`.

### The CrudTable component

`components/admin/CrudTable.vue` is the workhorse: every admin CRUD page is
~40 lines of `columns + formFields` configuration on top of it.

| Prop | Purpose |
|---|---|
| `resource` | An object exposing `{ list, retrieve, create, update, remove }`. Each `api/admin.js` export already has this shape. |
| `columns` | ant-design `<a-table>` column descriptors |
| `formFields` | Custom shape: `{ name, label, type, required, options, optionsResource, optionLabel, span, defaultValue, writeOnly, nullableEmpty, help, rules }` |
| `searchPlaceholder` | Search input placeholder |
| `defaultOrdering` | Initial `ordering=` query parameter |

`writeOnly: true` (used for password fields) keeps the value out of the read
view: on edit, leaving it empty submits without that key, so passwords don't
get reset.

`optionsResource` lets a select dropdown lazily load its choices from another
admin endpoint. Example from `UsersView.vue`:

```js
{
  name: 'department',
  label: '部門',
  type: 'select',
  optionsResource: adminDepartments,
  optionLabel: 'name',
  nullableEmpty: true,
  span: 12,
}
```

### Admin pages

| Path | Resource | Notes |
|---|---|---|
| `/admin/dashboard` | `monitoring/dashboard` | 4 KPIs + distributions + recent activity, 30 s auto-refresh |
| `/admin/logs` | `monitoring/logs` | 6 filters + detail Drawer rendering redacted JSON body |
| `/admin/fabs` | `admin/fabs` | CRUD |
| `/admin/departments` | `admin/departments` | CRUD with FK select to FAB |
| `/admin/users` | `admin/users` | CRUD with hashed-password write-only field |
| `/admin/experiments` | `admin/experiments` | CRUD |
| `/admin/equipment-types` | `admin/equipment-types` | CRUD |
| `/admin/equipment` | `admin/equipment` | CRUD; **department is required** (allocate-to-lab is the main task) |
| `/admin/experiment-requirements` | `admin/experiment-requirements` | M:N bridge between Experiment and EquipmentType + step order |
| `/admin/orders` | `admin/orders` | CRUD; status changes here bypass the state machine — use with care |
| `/admin/order-stages` | `admin/order-stages` | CRUD |
| `/admin/bookings` | `admin/bookings` | CRUD with start/end-time validation |

---

## Routing and role guards

`router/index.js` registers a `beforeEach` guard that:

1. Loads the user profile if a JWT exists but no user object.
2. Redirects authenticated users away from `meta.guest` routes (login / register).
3. Redirects unauthenticated users to `/login`.
4. Redirects users whose `auth.role` isn't in `meta.roles` to `/`.

Standalone routes (login, register, `/admin/*`) bypass the main shell and
render their own layout — `App.vue` checks via the `STANDALONE_PREFIXES` array.

---

## API client

`src/api/client.js` configures a single axios instance with:

- `baseURL` from `VITE_API_BASE` (default `http://127.0.0.1:8000/api`)
- A request interceptor that attaches `Authorization: Bearer <access_token>`
- A response interceptor that, on 401, attempts a single `/users/token/refresh/`
  call, queues other in-flight 401s, and replays them with the new token. If
  refresh fails, it clears tokens and redirects to `/login`.

Per-domain modules (`api/users.js`, `api/orders.js`, …) wrap specific endpoints
with named functions. `api/admin.js` exposes a uniform `resource(name)` factory
returning `{ list, retrieve, create, update, remove }`, so `CrudTable` doesn't
need to know which endpoint it's talking to.

---

## Common tasks

### Add a new admin CRUD page

1. Add an `admin<NewModel>` resource to `api/admin.js`:
   ```js
   export const adminNewModel = resource('new-model')
   ```
2. Create `views/admin/NewModelView.vue`:
   ```vue
   <template>
     <CrudTable
       :resource="adminNewModel"
       resource-label="新模型"
       title="新模型"
       :columns="columns"
       :form-fields="formFields"
     />
   </template>

   <script setup>
   import CrudTable from '../../components/admin/CrudTable.vue'
   import { adminNewModel } from '../../api/admin'

   const columns = [{ title: '名稱', dataIndex: 'name' }]
   const formFields = [
     { name: 'name', label: '名稱', type: 'text', required: true },
   ]
   </script>
   ```
3. Wire it up in `router/index.js` under the `/admin` parent.
4. Add the menu entry in `views/admin/AdminLayout.vue`'s `menuConfig`.

### Add a new role-restricted page

```js
{
  path: '/secret',
  component: SecretView,
  meta: { roles: ['lab_manager', 'superuser'] },
}
```

The router guard already enforces `meta.roles`. No further code needed.

### Translate a page

Already covered in [Theming and i18n § Add a new locale string](#add-a-new-locale-string).

### Run only one e2e spec

```bash
npx playwright test e2e/login.spec.js
npx playwright test -g "admin login"           # by test title regex
```
