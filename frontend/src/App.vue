<template>
  <a-config-provider
    :locale="antdLocale"
    :theme="antdTheme"
  >
    <!-- Guest views and the standalone /admin shell render their own layout. -->
    <router-view v-if="!showAppShell" />

    <!-- Default authenticated shell: collapsible sider + header + content. -->
    <a-layout v-else class="app-shell" :class="{ 'is-dark': settings.isDark }">
      <a-layout-sider
        v-model:collapsed="collapsed"
        collapsible
        :width="232"
        :theme="settings.isDark ? 'dark' : 'light'"
        class="app-sider"
      >
        <div class="brand">
          <ExperimentOutlined class="brand-icon" />
          <span v-if="!collapsed" class="brand-text">{{ t('common.appName') }}</span>
        </div>
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          :theme="settings.isDark ? 'dark' : 'light'"
          :items="menuItems"
          @click="onMenuClick"
        />
      </a-layout-sider>

      <a-layout>
        <a-layout-header class="app-header">
          <div class="header-left">
            <a-button type="text" @click="collapsed = !collapsed">
              <MenuFoldOutlined v-if="!collapsed" />
              <MenuUnfoldOutlined v-else />
            </a-button>
            <h2 class="page-heading">{{ pageHeading }}</h2>
          </div>

          <div class="header-right">
            <a-tooltip :title="t('settings.title')">
              <a-button type="text" @click="settingsOpen = true">
                <template #icon><SettingOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-button v-if="auth.isSuperuser" type="primary" @click="goAdmin">
              <template #icon><ThunderboltOutlined /></template>
              {{ t('nav.adminConsole') }}
            </a-button>
            <a-dropdown>
              <a-button type="text" class="user-trigger">
                <a-avatar style="background-color: #1890ff" size="small">
                  {{ avatarLetter }}
                </a-avatar>
                <span class="username">{{ auth.user?.username || '—' }}</span>
                <DownOutlined />
              </a-button>
              <template #overlay>
                <a-menu @click="onUserMenuClick">
                  <a-menu-item key="profile" disabled>
                    <UserOutlined />
                    <span>{{ auth.user?.email || '—' }}</span>
                  </a-menu-item>
                  <a-menu-item key="role" disabled>
                    <SafetyOutlined />
                    <span>{{ t('dashboard.role') }}: {{ roleLabel }}</span>
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout" danger>
                    <LogoutOutlined />
                    <span>{{ t('auth.logout') }}</span>
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </a-layout-header>

        <a-layout-content class="app-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </a-layout-content>

        <a-layout-footer class="app-footer">
          {{ t('common.appName') }} · {{ t('common.appSubtitle') }}
        </a-layout-footer>
      </a-layout>
    </a-layout>

    <!-- Settings drawer: language + theme. Available everywhere. -->
    <a-drawer
      v-model:open="settingsOpen"
      :title="t('settings.title')"
      placement="right"
      :width="320"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('settings.language')">
          <a-radio-group
            v-model:value="settings.locale"
            button-style="solid"
            @change="onLocaleChange"
          >
            <a-radio-button value="zh-TW">中文</a-radio-button>
            <a-radio-button value="en">English</a-radio-button>
          </a-radio-group>
        </a-form-item>

        <a-form-item :label="t('settings.theme')">
          <a-radio-group
            v-model:value="settings.theme"
            button-style="solid"
          >
            <a-radio-button value="light">
              <BulbOutlined />&nbsp;{{ t('settings.light') }}
            </a-radio-button>
            <a-radio-button value="dark">
              <BulbFilled />&nbsp;{{ t('settings.dark') }}
            </a-radio-button>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-drawer>
  </a-config-provider>
</template>

<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { theme as antdThemeApi } from 'ant-design-vue'
import zhTWLocale from 'ant-design-vue/es/locale/zh_TW'
import enUSLocale from 'ant-design-vue/es/locale/en_US'
import {
  AppstoreOutlined,
  BulbFilled,
  BulbOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  DownOutlined,
  ExperimentOutlined,
  FileAddOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProfileOutlined,
  SafetyOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from './stores/auth'
import { useSettingsStore } from './stores/settings'

const auth = useAuthStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()
const { t, locale: i18nLocale } = useI18n()

const collapsed = ref(false)
const settingsOpen = ref(false)

// Keep vue-i18n's active locale in lockstep with the persisted settings.
watch(
  () => settings.locale,
  (v) => {
    i18nLocale.value = v
  },
  { immediate: true },
)

function onLocaleChange() {
  // Touching the radio already flipped settings.locale; the watch above
  // propagates it to vue-i18n. This handler exists so future analytics
  // hooks have a single entry point.
}

const antdLocale = computed(() => (settings.locale === 'en' ? enUSLocale : zhTWLocale))
const antdTheme = computed(() => ({
  algorithm: settings.isDark ? antdThemeApi.darkAlgorithm : antdThemeApi.defaultAlgorithm,
  token: { colorPrimary: '#1890ff' },
}))

/** Routes that render their own layout. */
const STANDALONE_PREFIXES = ['/login', '/register', '/admin']

const showAppShell = computed(() => {
  if (!auth.isLoggedIn) return false
  return !STANDALONE_PREFIXES.some((p) => route.path.startsWith(p))
})

const menuConfig = computed(() => [
  { key: 'dashboard', label: t('nav.dashboard'), icon: DashboardOutlined, path: '/' },
  {
    key: 'my-orders',
    label: t('nav.myOrders'),
    icon: ProfileOutlined,
    path: '/orders',
    visible: () => auth.role === 'regular_employee' || auth.isSuperuser,
  },
  {
    key: 'create-order',
    label: t('nav.createOrder'),
    icon: FileAddOutlined,
    path: '/orders/create',
    visible: () => auth.role === 'regular_employee' || auth.isSuperuser,
  },
  {
    key: 'review',
    label: t('nav.review'),
    icon: CheckCircleOutlined,
    path: '/orders/review',
    visible: () => auth.isManager,
  },
  {
    key: 'tasks',
    label: t('nav.tasks'),
    icon: UnorderedListOutlined,
    path: '/orders/tasks',
    visible: () => auth.isMember,
  },
  { key: 'equipment', label: t('nav.equipment'), icon: AppstoreOutlined, path: '/equipment' },
])

const visibleMenu = computed(() =>
  menuConfig.value.filter((m) => !m.visible || m.visible()),
)

const menuItems = computed(() =>
  visibleMenu.value.map((m) => ({
    key: m.key,
    label: m.label,
    icon: () => h(m.icon),
  })),
)

const pathByKey = computed(() =>
  Object.fromEntries(visibleMenu.value.map((m) => [m.key, m.path])),
)
const labelByKey = computed(() =>
  Object.fromEntries(visibleMenu.value.map((m) => [m.key, m.label])),
)

const selectedKeys = ref([deriveKey(route.path)])

watch(
  () => route.path,
  (path) => {
    selectedKeys.value = [deriveKey(path)]
  },
)

function deriveKey(path) {
  const sorted = [...visibleMenu.value].sort((a, b) => b.path.length - a.path.length)
  const match = sorted.find((m) => path === m.path || path.startsWith(m.path + '/'))
  if (match) return match.key
  if (path === '/') return 'dashboard'
  return ''
}

const pageHeading = computed(() => labelByKey.value[selectedKeys.value[0]] || t('common.appName'))

const avatarLetter = computed(
  () => (auth.user?.username || '?').charAt(0).toUpperCase(),
)

const roleLabel = computed(() =>
  auth.role ? t(`roles.${auth.role}`) : '—',
)

function onMenuClick({ key }) {
  const path = pathByKey.value[key]
  if (path) router.push(path)
}

function onUserMenuClick({ key }) {
  if (key === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

function goAdmin() {
  router.push('/admin')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-sider {
  position: sticky;
  top: 0;
  height: 100vh;
  box-shadow: 1px 0 4px rgba(0, 21, 41, 0.04);
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 64px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-border);
  font-weight: 700;
  font-size: 16px;
  color: var(--c-primary);
  letter-spacing: 0.4px;
}
.brand-icon {
  font-size: 22px;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.06);
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-heading {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
}
.username {
  font-weight: 500;
}

.app-content {
  padding: 24px;
  min-height: calc(100vh - 64px - 70px);
}

.app-footer {
  text-align: center;
  background: transparent;
  padding: 16px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
