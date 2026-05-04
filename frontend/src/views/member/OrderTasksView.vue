<template>
  <div class="tasks-page">
    <a-page-header
      :title="t('tasks.title')"
      :sub-title="t('tasks.subtitle')"
      :back-icon="false"
    >
      <template #extra>
        <a-button @click="loadTasks" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </a-page-header>

    <a-alert
      type="info"
      show-icon
      :message="t('tasks.timeLockNote')"
      style="margin-bottom: 16px"
    />

    <a-table
      :columns="columns"
      :data-source="tasks"
      :loading="loading"
      row-key="id"
      :row-class-name="rowClassName"
      :pagination="{ pageSize: 20, showTotal: (n) => t('crud.paginationTotal', { total: n }) }"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'order_no'">
          <a-typography-text strong>{{ record.order_no || '—' }}</a-typography-text>
        </template>

        <template v-else-if="column.dataIndex === 'stage'">
          <div class="stage-cell">
            <span class="font-bold">{{ record.equipment_type_name }}</span>
            <a-tag style="margin-left: 6px">{{ t('review.step') }} {{ record.step_order }}</a-tag>
          </div>
        </template>

        <template v-else-if="column.dataIndex === 'equipment_code'">
          <a-tag v-if="record.equipment_code" color="blue">
            <ToolOutlined />&nbsp;{{ record.equipment_code }}
          </a-tag>
          <span v-else class="muted">—</span>
        </template>

        <template v-else-if="column.dataIndex === 'schedule'">
          <div class="schedule-cell">
            <div>{{ formatDate(record.schedule_start) }}</div>
            <div class="muted">→ {{ formatDate(record.schedule_end) }}</div>
          </div>
        </template>

        <template v-else-if="column.dataIndex === 'assignee'">
          <a-tag v-if="isAssignedToMe(record)" color="green">
            <StarFilled />&nbsp;{{ t('tasks.assignedToMe') }}
          </a-tag>
          <span v-else-if="record.assignee_name">{{ record.assignee_name }}</span>
          <span v-else class="muted">{{ t('common.notAssigned') }}</span>
        </template>

        <template v-else-if="column.dataIndex === '__actions__'">
          <template v-if="isAssignedToMe(record)">
            <a-tooltip
              v-if="!canComplete(record)"
              :title="t('tasks.notStartedTooltip')"
            >
              <a-button size="small" disabled>
                <template #icon><ClockCircleOutlined /></template>
                {{ t('tasks.notStarted') }}
              </a-button>
            </a-tooltip>
            <a-popconfirm
              v-else
              :title="t('tasks.confirmMarkDone', { step: record.step_order, type: record.equipment_type_name })"
              :ok-text="t('common.confirm')"
              :cancel-text="t('common.cancel')"
              @confirm="handleComplete(record)"
            >
              <a-button type="primary" size="small">
                <template #icon><CheckCircleOutlined /></template>
                {{ t('tasks.markDone') }}
              </a-button>
            </a-popconfirm>
          </template>
          <span v-else class="muted-text">{{ t('tasks.viewOnly') }}</span>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'

const { t } = useI18n()
import { message } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  StarFilled,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { completeStage, fetchStages } from '../../api/orders'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const tasks = ref([])
const loading = ref(false)

const columns = computed(() => [
  { title: t('orders.orderNo'), dataIndex: 'order_no', width: 200, fixed: 'left' },
  { title: t('tasks.stage'), dataIndex: 'stage', width: 220 },
  { title: t('tasks.equipment'), dataIndex: 'equipment_code', width: 160 },
  { title: t('orders.lotId'), dataIndex: 'lot_id', width: 120 },
  { title: t('tasks.schedule'), dataIndex: 'schedule', width: 240 },
  { title: t('tasks.assigneeStatus'), dataIndex: 'assignee', width: 140 },
  { title: t('tasks.actions'), dataIndex: '__actions__', width: 160, fixed: 'right' },
])

onMounted(loadTasks)

async function loadTasks() {
  loading.value = true
  try {
    const { data } = await fetchStages({ status: 'in_progress' })
    tasks.value = data.results || data || []
  } catch {
    message.error(t('tasks.loadFailed'))
  } finally {
    loading.value = false
  }
}

function isAssignedToMe(stage) {
  return stage.assignee === auth.user?.id
}

function canComplete(stage) {
  if (!stage.schedule_start) return true
  return dayjs().isAfter(dayjs(stage.schedule_start)) ||
    dayjs().isSame(dayjs(stage.schedule_start))
}

async function handleComplete(stage) {
  try {
    await completeStage(stage.id)
    message.success(t('tasks.completeOk', { step: stage.step_order }))
    await loadTasks()
  } catch (e) {
    message.error(e.response?.data?.detail || t('tasks.completeFailed'))
  }
}

function rowClassName(record) {
  return isAssignedToMe(record) ? 'my-task-row' : ''
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}
</script>

<style scoped>
.tasks-page {
  padding: 0;
}
:deep(.my-task-row) {
  background: rgba(82, 196, 26, 0.05);
}
:deep(.my-task-row:hover > td) {
  background: rgba(82, 196, 26, 0.1) !important;
}
.stage-cell {
  display: flex;
  align-items: center;
}
.font-bold {
  font-weight: 600;
}
.schedule-cell {
  font-size: 12px;
  line-height: 1.6;
}
.muted {
  color: var(--c-text-muted);
  font-style: italic;
}
.muted-text {
  color: var(--c-text-muted);
  font-size: 12px;
}
</style>
