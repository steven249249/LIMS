<template>
  <a-layout class="admin-shell">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      :width="240"
      theme="dark"
      class="admin-sider"
    >
      <div class="admin-brand">
        <ThunderboltOutlined class="brand-icon" />
        <span v-if="!collapsed" class="brand-text">{{ t('admin.consoleBrand') }}</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        mode="inline"
        theme="dark"
        :items="menuItems"
        @click="onMenuClick"
      />
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="admin-header">
        <div class="admin-header-left">
          <a-breadcrumb>
            <a-breadcrumb-item>
              <HomeOutlined />
              <span>&nbsp;{{ t('admin.breadcrumbHome') }}</span>
            </a-breadcrumb-item>
            <a-breadcrumb-item>{{ currentLabel }}</a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="admin-header-right">
          <a-tag color="processing" v-if="auth.user">
            <UserOutlined />&nbsp;{{ auth.user.username }} ({{ auth.role }})
          </a-tag>
          <a-button type="link" @click="goHome">
            <template #icon><RollbackOutlined /></template>
            {{ t('admin.backToMain') }}
          </a-button>
          <a-button type="link" danger @click="onLogout">
            <template #icon><LogoutOutlined /></template>
            {{ t('auth.logout') }}
          </a-button>
        </div>
      </a-layout-header>

      <a-layout-content class="admin-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </a-layout-content>

      <a-layout-footer class="admin-footer">
        {{ t('admin.consoleBrand') }} &nbsp;·&nbsp; {{ t('common.appFullName') }}
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ApartmentOutlined,
  AppstoreOutlined,
  BankOutlined,
  CalendarOutlined,
  ClusterOutlined,
  ContainerOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  HomeOutlined,
  LogoutOutlined,
  NodeIndexOutlined,
  ProfileOutlined,
  RollbackOutlined,
  TagsOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()

const collapsed = ref(false)

const menuConfig = computed(() => [
  { key: 'dashboard', label: t('admin.nav.dashboard'), icon: DashboardOutlined, path: '/admin/dashboard' },
  { key: 'logs', label: t('admin.nav.logs'), icon: FileSearchOutlined, path: '/admin/logs' },
  { type: 'divider' },
  { key: 'fabs', label: t('admin.nav.fabs'), icon: BankOutlined, path: '/admin/fabs' },
  { key: 'departments', label: t('admin.nav.departments'), icon: ApartmentOutlined, path: '/admin/departments' },
  { key: 'wafer-lots', label: t('admin.nav.waferLots'), icon: TagsOutlined, path: '/admin/wafer-lots' },
  { key: 'users', label: t('admin.nav.users'), icon: TeamOutlined, path: '/admin/users' },
  { type: 'divider' },
  { key: 'experiments', label: t('admin.nav.experiments'), icon: ExperimentOutlined, path: '/admin/experiments' },
  { key: 'equipment-types', label: t('admin.nav.equipmentTypes'), icon: AppstoreOutlined, path: '/admin/equipment-types' },
  { key: 'equipment', label: t('admin.nav.equipment'), icon: ToolOutlined, path: '/admin/equipment' },
  {
    key: 'experiment-requirements',
    label: t('admin.nav.experimentRequirements'),
    icon: ClusterOutlined,
    path: '/admin/experiment-requirements',
  },
  { type: 'divider' },
  { key: 'orders', label: t('admin.nav.orders'), icon: ProfileOutlined, path: '/admin/orders' },
  { key: 'order-stages', label: t('admin.nav.orderStages'), icon: NodeIndexOutlined, path: '/admin/order-stages' },
  { key: 'bookings', label: t('admin.nav.bookings'), icon: CalendarOutlined, path: '/admin/bookings' },
])

const menuItems = computed(() =>
  menuConfig.value.map((item, idx) =>
    item.type === 'divider'
      ? { type: 'divider', key: `d-${idx}` }
      : { key: item.key, label: item.label, icon: () => h(item.icon) },
  ),
)

const pathByKey = computed(() =>
  Object.fromEntries(menuConfig.value.filter((m) => m.key).map((m) => [m.key, m.path])),
)
const labelByKey = computed(() =>
  Object.fromEntries(menuConfig.value.filter((m) => m.key).map((m) => [m.key, m.label])),
)

const selectedKeys = ref([deriveKey(route.path)])

watch(
  () => route.path,
  (path) => {
    selectedKeys.value = [deriveKey(path)]
  },
)

function deriveKey(path) {
  const segment = path.split('/')[2] || 'dashboard'
  return segment in pathByKey.value ? segment : 'dashboard'
}

const currentLabel = computed(
  () => labelByKey.value[selectedKeys.value[0]] || t('admin.consoleSubtitle'),
)

function onMenuClick({ key }) {
  router.push(pathByKey.value[key])
}

function goHome() {
  router.push('/')
}

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-shell {
  min-height: 100vh;
}

.admin-sider {
  position: sticky;
  top: 0;
  height: 100vh;
}

.admin-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 64px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.6px;
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.18), transparent);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-icon {
  font-size: 22px;
  color: #1890ff;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--c-bg-card);
  border-bottom: 1px solid var(--c-border);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.admin-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-content {
  margin: 24px;
  padding: 24px;
  background: var(--c-bg-card);
  color: var(--c-text);
  min-height: calc(100vh - 64px - 70px - 48px);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.admin-footer {
  text-align: center;
  color: var(--c-text-muted);
  background: transparent;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
