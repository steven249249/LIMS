<template>
  <div class="orders-page">
    <a-page-header :title="t('orders.title')" :sub-title="t('orders.subtitle')" :back-icon="false">
      <template #extra>
        <a-button @click="loadOrders" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
        <a-button type="primary" @click="$router.push('/orders/create')">
          <template #icon><FileAddOutlined /></template>
          {{ t('nav.createOrder') }}
        </a-button>
      </template>
    </a-page-header>

    <a-table
      :columns="columns"
      :data-source="orders"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 10, showTotal: (n) => t('crud.paginationTotal', { total: n }) }"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'order_no'">
          <a-typography-text strong>{{ record.order_no }}</a-typography-text>
        </template>
        <template v-else-if="column.dataIndex === 'progress'">
          <div class="relay-mini-track">
            <a-tooltip
              v-for="s in record.stages || []"
              :key="s.id"
              :title="`${s.department_name} · ${statusLabel(s.status)}`"
            >
              <span class="relay-dot" :class="`dot-${s.status}`"></span>
            </a-tooltip>
            <span v-if="!(record.stages || []).length" class="muted">{{ t('orders.noStages') }}</span>
          </div>
        </template>
        <template v-else-if="column.dataIndex === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.dataIndex === 'is_urgent'">
          <a-tag v-if="record.is_urgent" color="red">{{ t('orders.urgent') }}</a-tag>
          <span v-else class="muted">—</span>
        </template>
        <template v-else-if="column.dataIndex === '__actions__'">
          <a-button type="link" size="small" @click="viewDetail(record)">
            <template #icon><EyeOutlined /></template>
            {{ t('common.detail') }}
          </a-button>
        </template>
      </template>
    </a-table>

    <a-drawer
      v-model:open="detailOpen"
      :title="selectedOrder ? `${t('orders.detailDrawerTitle')}: ${selectedOrder.order_no}` : ''"
      width="720"
      placement="right"
    >
      <template v-if="selectedOrder">
        <a-card :title="t('orders.relayProgress')" :bordered="false" size="small" class="detail-card">
          <a-steps
            v-if="(selectedOrder.stages || []).length"
            :current="currentStepIndex"
            size="small"
            :status="overallStepsStatus"
          >
            <a-step
              v-for="stage in selectedOrder.stages"
              :key="stage.id"
              :title="stage.department_name"
              :status="stepStatus(stage)"
            >
              <template #description>
                <div class="step-desc">
                  <a-tag :color="stageStatusColor(stage.status)">
                    {{ statusLabel(stage.status) }}
                  </a-tag>
                </div>
              </template>
            </a-step>
          </a-steps>
          <a-empty v-else :description="t('orders.noRelayStages')" />
        </a-card>

        <a-divider />

        <a-descriptions :title="t('orders.generalInfo')" bordered :column="2" size="small">
          <a-descriptions-item :label="t('orders.orderNo')" :span="2">
            <code>{{ selectedOrder.order_no }}</code>
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.experiment')">
            {{ selectedOrder.experiment_name }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.lotId')">
            {{ selectedOrder.lot_id || '—' }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.overallStatus')">
            <a-tag :color="statusColor(selectedOrder.status)">
              {{ statusLabel(selectedOrder.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.urgent')">
            <a-tag v-if="selectedOrder.is_urgent" color="red">{{ t('orders.urgent') }}</a-tag>
            <span v-else>{{ t('common.no') }}</span>
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.createdAt')" :span="2">
            {{ formatDate(selectedOrder.created_at) }}
          </a-descriptions-item>
        </a-descriptions>

        <a-divider />

        <a-descriptions
          v-if="currentStage"
          :title="t('orders.currentStation')"
          bordered
          :column="1"
          size="small"
        >
          <a-descriptions-item :label="t('orders.laboratory')">
            {{ currentStage.department_name }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('orders.operator')">
            {{ currentStage.assignee_name || t('common.notAssigned') }}
          </a-descriptions-item>
          <a-descriptions-item v-if="currentStage.schedule_start" :label="t('orders.schedule')">
            {{ formatDate(currentStage.schedule_start) }}
            →
            {{ formatDate(currentStage.schedule_end) }}
          </a-descriptions-item>
        </a-descriptions>

        <a-alert
          v-if="selectedOrder.rejection_reason"
          type="error"
          show-icon
          :message="`${t('orders.rejectReason')}: ${selectedOrder.rejection_reason}`"
          style="margin-top: 16px"
        />

        <a-divider />

        <div class="remark-block">
          <h4>{{ t('orders.remark') }}</h4>
          <p v-if="selectedOrder.remark">{{ selectedOrder.remark }}</p>
          <a-empty v-else :description="t('orders.noRemark')" :image-style="{ height: 40 }" />
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import {
  EyeOutlined,
  FileAddOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import { fetchOrder, fetchOrders } from '../../api/orders'

const { t } = useI18n()

const orders = ref([])
const loading = ref(false)
const detailOpen = ref(false)
const selectedOrder = ref(null)

const columns = computed(() => [
  { title: t('orders.orderNo'), dataIndex: 'order_no', width: 200, fixed: 'left' },
  { title: t('orders.experiment'), dataIndex: 'experiment_name', width: 220 },
  { title: t('orders.lotId'), dataIndex: 'lot_id', width: 130 },
  { title: t('orders.progress'), dataIndex: 'progress', width: 200 },
  { title: t('orders.urgent'), dataIndex: 'is_urgent', width: 80 },
  { title: t('orders.status'), dataIndex: 'status', width: 110 },
  { title: '', dataIndex: '__actions__', width: 100, fixed: 'right' },
])

onMounted(loadOrders)

async function loadOrders() {
  loading.value = true
  try {
    const { data } = await fetchOrders()
    orders.value = data.results || data || []
  } catch (e) {
    message.error(t('orders.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function viewDetail(record) {
  try {
    const { data } = await fetchOrder(record.id)
    selectedOrder.value = data
    detailOpen.value = true
  } catch {
    message.error(t('orders.loadDetailFailed'))
  }
}

const currentStage = computed(() => {
  if (!selectedOrder.value?.stages?.length) return null
  return (
    selectedOrder.value.stages.find((s) => s.status !== 'done') ||
    selectedOrder.value.stages[selectedOrder.value.stages.length - 1]
  )
})

const currentStepIndex = computed(() => {
  if (!selectedOrder.value?.stages?.length) return 0
  const idx = selectedOrder.value.stages.findIndex((s) => s.status !== 'done')
  return idx === -1 ? selectedOrder.value.stages.length - 1 : idx
})

const overallStepsStatus = computed(() => {
  if (!selectedOrder.value) return 'process'
  if (selectedOrder.value.status === 'rejected') return 'error'
  if (selectedOrder.value.status === 'done') return 'finish'
  return 'process'
})

function stepStatus(stage) {
  return {
    pending: 'wait', waiting: 'wait',
    in_progress: 'process', done: 'finish', rejected: 'error',
  }[stage.status] || 'wait'
}

function statusLabel(s) {
  return t(`orders.statusLabels.${s}`, s)
}
function statusColor(s) {
  return {
    created: 'default', waiting: 'warning', pending: 'default',
    in_progress: 'processing', done: 'success', rejected: 'error',
  }[s] || 'default'
}
function stageStatusColor(s) {
  return statusColor(s)
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}
</script>

<style scoped>
.orders-page {
  padding: 0;
}
.relay-mini-track {
  display: flex;
  align-items: center;
  gap: 6px;
}
.relay-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d9d9d9;
  display: inline-block;
}
.dot-done { background: #52c41a; }
.dot-in_progress {
  background: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.2);
  animation: pulse 1.6s infinite;
}
.dot-waiting { background: #faad14; }
.dot-pending { background: #d9d9d9; }
.dot-rejected { background: #f5222d; }

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}
.muted {
  color: var(--c-text-muted);
  font-style: italic;
  font-size: 12px;
}
.detail-card :deep(.ant-card-body) {
  padding: 16px 12px;
}
.step-desc {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.55);
}
.remark-block h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
</style>
