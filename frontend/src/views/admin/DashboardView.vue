<template>
  <div class="dash">
    <a-page-header :title="t('admin.dashboard.title')" :sub-title="t('admin.dashboard.subtitle')">
      <template #extra>
        <a-tooltip :title="t('admin.dashboard.autoRefresh')">
          <a-switch
            v-model:checked="autoRefresh"
            :checked-children="t('admin.dashboard.autoOn')"
            :un-checked-children="t('admin.dashboard.autoOff')"
          />
        </a-tooltip>
        <a-button @click="load" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </a-page-header>

    <a-skeleton :loading="loading && !stats" active>
      <template v-if="stats">
        <a-row :gutter="[16, 16]">
          <a-col :xs="24" :sm="12" :md="6">
            <a-card hoverable>
              <a-statistic
                :title="t('admin.dashboard.kpiTotalOrders')"
                :value="stats.orders.total"
                :value-style="{ color: '#1890ff' }"
              >
                <template #prefix><ProfileOutlined /></template>
              </a-statistic>
              <div class="stat-foot">
                {{ t('admin.dashboard.since7dHint', { n: stats.orders.created_last_7d }) }}
              </div>
            </a-card>
          </a-col>

          <a-col :xs="24" :sm="12" :md="6">
            <a-card hoverable>
              <a-statistic
                :title="t('admin.dashboard.kpiInProgress')"
                :value="stats.orders.by_status.in_progress || 0"
                :value-style="{ color: '#fa8c16' }"
              >
                <template #prefix><ThunderboltOutlined /></template>
              </a-statistic>
              <div class="stat-foot">
                {{ t('admin.dashboard.waitingHint', { n: stats.orders.by_status.waiting || 0 }) }}
              </div>
            </a-card>
          </a-col>

          <a-col :xs="24" :sm="12" :md="6">
            <a-card hoverable>
              <a-statistic
                :title="t('admin.dashboard.kpiEquipmentUsage')"
                :value="equipmentUsage"
                :precision="1"
                suffix="%"
                :value-style="{ color: equipmentUsage > 70 ? '#cf1322' : '#3f8600' }"
              >
                <template #prefix><ToolOutlined /></template>
              </a-statistic>
              <div class="stat-foot">
                {{ t('admin.dashboard.occupiedHint', {
                    n: stats.equipment.by_status.occupied || 0,
                    total: stats.equipment.total,
                }) }}
              </div>
            </a-card>
          </a-col>

          <a-col :xs="24" :sm="12" :md="6">
            <a-card hoverable>
              <a-statistic
                :title="t('admin.dashboard.kpi24hTraffic')"
                :value="stats.activity.last_24h_total"
                :value-style="{ color: '#722ed1' }"
              >
                <template #prefix><ApiOutlined /></template>
              </a-statistic>
              <div class="stat-foot">
                {{ t('admin.dashboard.avgRespHint', { ms: stats.activity.avg_duration_ms_24h }) }}
              </div>
            </a-card>
          </a-col>
        </a-row>

        <a-row :gutter="[16, 16]" style="margin-top: 16px">
          <a-col :xs="24" :md="12">
            <a-card :title="t('admin.dashboard.orderStatusDist')" :bordered="false">
              <a-list :data-source="orderStatusList" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <div class="row-status">
                      <a-tag :color="statusColor(item.key)">{{ statusLabel(item.key) }}</a-tag>
                      <a-progress
                        :percent="percentOf(item.value, stats.orders.total)"
                        :stroke-color="statusHex(item.key)"
                        size="small"
                        style="flex: 1; margin: 0 12px"
                      />
                      <strong>{{ item.value }}</strong>
                    </div>
                  </a-list-item>
                </template>
              </a-list>
            </a-card>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-card :title="t('admin.dashboard.equipmentStatusDist')" :bordered="false">
              <a-list :data-source="equipmentStatusList" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <div class="row-status">
                      <a-tag :color="statusColor(item.key)">{{ statusLabel(item.key) }}</a-tag>
                      <a-progress
                        :percent="percentOf(item.value, stats.equipment.total)"
                        :stroke-color="statusHex(item.key)"
                        size="small"
                        style="flex: 1; margin: 0 12px"
                      />
                      <strong>{{ item.value }}</strong>
                    </div>
                  </a-list-item>
                </template>
              </a-list>
            </a-card>
          </a-col>
        </a-row>

        <a-row :gutter="[16, 16]" style="margin-top: 16px">
          <a-col :xs="24" :md="12">
            <a-card :title="t('admin.dashboard.userRoleDist')" :bordered="false">
              <a-row :gutter="[8, 8]">
                <a-col :span="12" v-for="(value, key) in stats.users.by_role" :key="key">
                  <a-statistic
                    :title="roleLabel(key)"
                    :value="value"
                    :value-style="{ fontSize: '20px', color: roleHex(key) }"
                  />
                </a-col>
              </a-row>
              <a-divider style="margin: 12px 0" />
              <div class="footer-note">
                {{ t('admin.dashboard.totalUsers', { total: stats.users.total, active: stats.users.active }) }}
              </div>
            </a-card>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-card :title="t('admin.dashboard.action24hDist')" :bordered="false">
              <a-empty
                v-if="!Object.keys(stats.activity.last_24h_by_action).length"
                :description="t('admin.dashboard.noRecent')"
              />
              <a-list v-else :data-source="actionsList" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <div class="row-status">
                      <a-tag :color="actionColor(item.key)">{{ actionLabel(item.key) }}</a-tag>
                      <a-progress
                        :percent="percentOf(item.value, stats.activity.last_24h_total)"
                        :stroke-color="actionHex(item.key)"
                        size="small"
                        style="flex: 1; margin: 0 12px"
                      />
                      <strong>{{ item.value }}</strong>
                    </div>
                  </a-list-item>
                </template>
              </a-list>
            </a-card>
          </a-col>
        </a-row>

        <a-card
          :title="t('admin.dashboard.recentActivity')"
          :bordered="false"
          style="margin-top: 16px"
          :body-style="{ padding: 0 }"
        >
          <template #extra>
            <a-button type="link" @click="goToLogs">{{ t('common.viewAll') }}</a-button>
          </template>
          <a-table
            :columns="logColumns"
            :data-source="recentLogs"
            :pagination="false"
            :loading="logsLoading"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'action_type'">
                <a-tag :color="actionColor(record.action_type)">
                  {{ record.action_type_display }}
                </a-tag>
              </template>
              <template v-else-if="column.dataIndex === 'http_method'">
                <a-tag :color="methodColor(record.http_method)">{{ record.http_method }}</a-tag>
              </template>
              <template v-else-if="column.dataIndex === 'status_code'">
                <a-tag :color="statusCodeColor(record.status_code)">{{ record.status_code }}</a-tag>
              </template>
              <template v-else-if="column.dataIndex === 'timestamp'">
                {{ formatDate(record.timestamp) }}
              </template>
            </template>
          </a-table>
        </a-card>

        <div class="generated-at">
          {{ t('admin.dashboard.generatedAt', { time: formatDate(stats.generated_at) }) }}
        </div>
      </template>
    </a-skeleton>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import {
  ApiOutlined,
  ProfileOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { fetchActivityLogs, fetchAdminDashboard } from '../../api/admin'

const router = useRouter()
const { t } = useI18n()
const stats = ref(null)
const loading = ref(false)
const recentLogs = ref([])
const logsLoading = ref(false)
const autoRefresh = ref(true)
let timer = null

const logColumns = computed(() => [
  { title: t('admin.logs.colTime'), dataIndex: 'timestamp', width: 170 },
  { title: t('admin.logs.colUser'), dataIndex: 'username', width: 140 },
  { title: t('admin.logs.colAction'), dataIndex: 'action_type', width: 100 },
  { title: t('admin.logs.colMethod'), dataIndex: 'http_method', width: 80 },
  { title: t('admin.logs.colPath'), dataIndex: 'path', ellipsis: true },
  { title: t('admin.logs.colStatus'), dataIndex: 'status_code', width: 80 },
  { title: t('admin.logs.colDuration'), dataIndex: 'duration_ms', width: 100 },
])

const orderStatusList = computed(() =>
  stats.value
    ? Object.entries(stats.value.orders.by_status).map(([key, value]) => ({ key, value }))
    : [],
)

const equipmentStatusList = computed(() =>
  stats.value
    ? Object.entries(stats.value.equipment.by_status).map(([key, value]) => ({ key, value }))
    : [],
)

const actionsList = computed(() =>
  stats.value
    ? Object.entries(stats.value.activity.last_24h_by_action).map(([key, value]) => ({ key, value }))
    : [],
)

const equipmentUsage = computed(() => {
  if (!stats.value || !stats.value.equipment.total) return 0
  const occupied = stats.value.equipment.by_status.occupied || 0
  return (occupied / stats.value.equipment.total) * 100
})

async function load() {
  loading.value = true
  logsLoading.value = true
  try {
    const [{ data: dash }, { data: logs }] = await Promise.all([
      fetchAdminDashboard(),
      fetchActivityLogs({ page: 1, page_size: 10 }),
    ])
    stats.value = dash
    recentLogs.value = logs.results || []
  } finally {
    loading.value = false
    logsLoading.value = false
  }
}

onMounted(() => {
  load()
  startTimer()
})

onBeforeUnmount(() => {
  stopTimer()
})

watch(autoRefresh, (val) => (val ? startTimer() : stopTimer()))

function startTimer() {
  stopTimer()
  if (autoRefresh.value) timer = setInterval(load, 30_000)
}
function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function goToLogs() {
  router.push('/admin/logs')
}

function percentOf(value, total) {
  if (!total) return 0
  return Number(((value / total) * 100).toFixed(1))
}

function statusLabel(key) {
  // Stage / order / equipment statuses share keys; try the three catalogue
  // namespaces in order so we always get a meaningful translation.
  return t(`equipmentStatus.${key}`, t(`orders.statusLabels.${key}`, t(`stageStatus.${key}`, key)))
}
function statusColor(key) {
  const map = {
    available: 'success', occupied: 'warning', maintenance: 'error', inactive: 'default',
    pending: 'default', waiting: 'warning', in_progress: 'processing', done: 'success',
    rejected: 'error', created: 'default',
  }
  return map[key] || 'default'
}
function statusHex(key) {
  const map = {
    available: '#52c41a', occupied: '#faad14', maintenance: '#f5222d',
    inactive: '#bfbfbf', pending: '#bfbfbf', waiting: '#faad14',
    in_progress: '#1890ff', done: '#52c41a', rejected: '#f5222d',
    created: '#bfbfbf',
  }
  return map[key] || '#bfbfbf'
}

function roleLabel(key) {
  return t(`roles.${key}`, key)
}
function roleHex(key) {
  const map = {
    superuser: '#cf1322',
    lab_manager: '#1d39c4',
    lab_member: '#08979c',
    regular_employee: '#595959',
  }
  return map[key] || '#595959'
}

function actionLabel(key) {
  return t(`admin.actions.${key}`, key)
}
function actionColor(key) {
  const map = {
    login: 'cyan', logout: 'default', create: 'green', read: 'blue',
    update: 'orange', delete: 'red', other: 'default',
  }
  return map[key] || 'default'
}
function actionHex(key) {
  const map = {
    login: '#13c2c2', logout: '#bfbfbf', create: '#52c41a', read: '#1890ff',
    update: '#fa8c16', delete: '#f5222d', other: '#bfbfbf',
  }
  return map[key] || '#bfbfbf'
}

function methodColor(method) {
  const map = { GET: 'blue', POST: 'green', PUT: 'orange', PATCH: 'orange', DELETE: 'red' }
  return map[method] || 'default'
}
function statusCodeColor(code) {
  if (code < 300) return 'success'
  if (code < 400) return 'processing'
  if (code < 500) return 'warning'
  return 'error'
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '—'
}
</script>

<style scoped>
.dash {
  padding: 0;
}
.stat-foot {
  margin-top: 12px;
  color: var(--c-text-muted);
  font-size: 12px;
}
.row-status {
  display: flex;
  align-items: center;
  width: 100%;
}
.footer-note {
  color: var(--c-text-muted);
  font-size: 12px;
}
.generated-at {
  margin-top: 16px;
  text-align: right;
  color: var(--c-text-muted);
  font-size: 12px;
}
</style>
