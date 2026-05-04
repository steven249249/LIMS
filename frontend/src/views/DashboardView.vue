<template>
  <div class="dash">
    <a-page-header
      :title="t('dashboard.welcome', { name: auth.user?.username || '—' })"
      :sub-title="welcomeSub"
      :back-icon="false"
    >
      <template #extra>
        <a-tag :color="roleColor">
          <SafetyOutlined />&nbsp;{{ roleLabel }}
        </a-tag>
        <a-button v-if="canCreateOrder" type="primary" @click="goCreate">
          <template #icon><FileAddOutlined /></template>
          {{ t('nav.createOrder') }}
        </a-button>
      </template>
    </a-page-header>

    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :md="6">
        <a-card hoverable>
          <a-statistic
            :title="t('dashboard.totalOrders')"
            :value="stats.total"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix><ProfileOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card hoverable>
          <a-statistic
            :title="t('dashboard.waiting')"
            :value="stats.waiting"
            :value-style="{ color: '#faad14' }"
          >
            <template #prefix><ClockCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card hoverable>
          <a-statistic
            :title="t('dashboard.inProgress')"
            :value="stats.in_progress"
            :value-style="{ color: '#722ed1' }"
          >
            <template #prefix><ThunderboltOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card hoverable>
          <a-statistic
            :title="t('dashboard.done')"
            :value="stats.done"
            :value-style="{ color: '#52c41a' }"
          >
            <template #prefix><CheckCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :md="16">
        <a-card :title="t('dashboard.recentOrders')" :bordered="false" :body-style="{ padding: 0 }">
          <a-table
            :columns="orderColumns"
            :data-source="recentOrders"
            :pagination="false"
            :loading="loading"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'status'">
                <a-tag :color="statusColor(record.status)">
                  {{ statusLabel(record.status) }}
                </a-tag>
              </template>
              <template v-else-if="column.dataIndex === 'created_at'">
                {{ formatDate(record.created_at) }}
              </template>
              <template v-else-if="column.dataIndex === 'is_urgent'">
                <a-tag v-if="record.is_urgent" color="red">{{ t('orders.urgent') }}</a-tag>
                <span v-else class="muted">—</span>
              </template>
            </template>
          </a-table>
          <a-empty
            v-if="!loading && !recentOrders.length"
            :description="t('dashboard.noOrders')"
            style="padding: 40px 0"
          />
        </a-card>
      </a-col>

      <a-col :xs="24" :md="8">
        <a-card :title="t('dashboard.quickActions')" :bordered="false">
          <a-space direction="vertical" size="middle" style="width: 100%">
            <a-button v-if="canCreateOrder" block size="large" type="primary" @click="goCreate">
              <template #icon><FileAddOutlined /></template>
              {{ t('nav.createOrder') }}
            </a-button>
            <a-button v-if="canCreateOrder" block size="large" @click="goOrders">
              <template #icon><UnorderedListOutlined /></template>
              {{ t('nav.myOrders') }}
            </a-button>
            <a-button v-if="auth.isManager" block size="large" @click="goReview">
              <template #icon><CheckCircleOutlined /></template>
              {{ t('nav.review') }}
            </a-button>
            <a-button v-if="auth.isMember" block size="large" @click="goTasks">
              <template #icon><ThunderboltOutlined /></template>
              {{ t('nav.tasks') }}
            </a-button>
            <a-button block size="large" @click="goEquipment">
              <template #icon><AppstoreOutlined /></template>
              {{ t('nav.equipment') }}
            </a-button>
            <a-button v-if="auth.isSuperuser" block size="large" type="primary" ghost @click="goAdmin">
              <template #icon><DashboardOutlined /></template>
              {{ t('nav.adminConsole') }}
            </a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import {
  AppstoreOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  FileAddOutlined,
  ProfileOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '../stores/auth'
import { fetchOrders } from '../api/orders'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const stats = ref({ total: 0, waiting: 0, in_progress: 0, done: 0 })
const recentOrders = ref([])
const loading = ref(false)

const orderColumns = computed(() => [
  { title: t('orders.orderNo'), dataIndex: 'order_no', width: 180 },
  { title: t('orders.experiment'), dataIndex: 'experiment_name' },
  { title: t('orders.lotId'), dataIndex: 'lot_id', width: 110 },
  { title: t('orders.urgent'), dataIndex: 'is_urgent', width: 80 },
  { title: t('orders.status'), dataIndex: 'status', width: 110 },
  { title: t('orders.createdAt'), dataIndex: 'created_at', width: 170 },
])

const ROLE_COLORS = {
  superuser: 'red',
  lab_manager: 'geekblue',
  lab_member: 'cyan',
  regular_employee: 'default',
}
const roleLabel = computed(() =>
  auth.role ? t(`roles.${auth.role}`) : '—',
)
const roleColor = computed(() => ROLE_COLORS[auth.role] || 'default')

const welcomeSub = computed(() => {
  const today = dayjs().format('YYYY-MM-DD dddd')
  return t('dashboard.todayIs', { date: today })
})

const canCreateOrder = computed(
  () => auth.role === 'regular_employee' || auth.isSuperuser,
)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await fetchOrders()
    const orders = data.results || data || []
    stats.value = {
      total: orders.length,
      waiting: orders.filter((o) => o.status === 'waiting').length,
      in_progress: orders.filter((o) => o.status === 'in_progress').length,
      done: orders.filter((o) => o.status === 'done').length,
    }
    recentOrders.value = orders.slice(0, 5)
  } catch {
    /* 對於部分角色 (e.g. lab_member 沒 orders 權限) 忽略錯誤 */
  } finally {
    loading.value = false
  }
})

function statusLabel(s) {
  return t(`orders.statusLabels.${s}`, s)
}
function statusColor(s) {
  return {
    created: 'default', waiting: 'warning', in_progress: 'processing',
    done: 'success', rejected: 'error',
  }[s] || 'default'
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}

function goCreate() { router.push('/orders/create') }
function goOrders() { router.push('/orders') }
function goReview() { router.push('/orders/review') }
function goTasks() { router.push('/orders/tasks') }
function goEquipment() { router.push('/equipment') }
function goAdmin() { router.push('/admin') }
</script>

<style scoped>
.dash {
  padding: 0;
}
.muted {
  color: var(--c-text-muted);
}
</style>
