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
          <h4>{{ t('orders.requirements') }}</h4>
          <p v-if="selectedOrder.requirements" style="white-space: pre-wrap">{{ selectedOrder.requirements }}</p>
          <a-empty v-else :description="t('orders.noRequirements')" :image-style="{ height: 40 }" />
        </div>

        <a-divider />

        <div class="remark-block">
          <h4>{{ t('orders.remark') }}</h4>
          <p v-if="selectedOrder.remark" style="white-space: pre-wrap">{{ selectedOrder.remark }}</p>
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

function statusLabel(s) {
  return t(`orders.statusLabels.${s}`, s)
}
function statusColor(s) {
  return {
    created: 'default', waiting: 'warning', pending: 'default',
    in_progress: 'processing', done: 'success', rejected: 'error',
  }[s] || 'default'
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}
</script>

<style scoped>
.orders-page {
  padding: 0;
}
.muted {
  color: var(--c-text-muted);
  font-style: italic;
  font-size: 12px;
}
.remark-block h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
</style>
