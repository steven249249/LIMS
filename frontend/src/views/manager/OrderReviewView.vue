<template>
  <div class="review-page">
    <a-page-header
      :title="t('review.title')"
      :sub-title="t('review.subtitle')"
      :back-icon="false"
    >
      <template #extra>
        <a-button @click="reloadAll" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </a-page-header>

    <a-card :title="t('review.timelineTitle')" :bordered="false" class="timeline-wrapper">
      <TimelineChart
        :grouped-equipments="groupedEquipments"
        :bookings="allBookings"
        @booking-click="openEditBooking"
      />
    </a-card>

    <a-card
      :title="t('review.waitingStagesTitle')"
      :bordered="false"
      style="margin-top: 16px"
      :body-style="{ padding: 0 }"
    >
      <a-table
        :columns="waitingColumns"
        :data-source="waitingStages"
        row-key="id"
        :pagination="false"
        :loading="loading"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'step_order'">
            <a-tag color="blue">{{ t('review.step') }} {{ record.step_order }}</a-tag>
          </template>
          <template v-else-if="column.dataIndex === '__actions__'">
            <a-space>
              <a-button type="primary" size="small" @click="openApprove(record)">
                <template #icon><CheckOutlined /></template>
                {{ t('review.approveSchedule') }}
              </a-button>
              <a-button danger size="small" @click="openReject(record)">
                <template #icon><CloseOutlined /></template>
                {{ t('review.reject') }}
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
      <a-empty
        v-if="!loading && !waitingStages.length"
        :description="t('review.noWaiting')"
        style="padding: 40px 0"
      />
    </a-card>

    <a-card
      :title="t('review.activeStagesTitle')"
      :bordered="false"
      style="margin-top: 16px"
      :body-style="{ padding: 0 }"
    >
      <a-table
        :columns="activeColumns"
        :data-source="activeStages"
        row-key="id"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'step_order'">
            <a-tag color="blue">{{ t('review.step') }} {{ record.step_order }}</a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'assignee_name'">
            <a-tag v-if="record.assignee_name" color="cyan">
              <UserOutlined />&nbsp;{{ record.assignee_name }}
            </a-tag>
            <span v-else class="muted">{{ t('common.notAssigned') }}</span>
          </template>
          <template v-else-if="column.dataIndex === 'schedule'">
            <div class="schedule-cell">
              <div>{{ formatDate(record.schedule_start) }}</div>
              <div class="muted">→ {{ formatDate(record.schedule_end) }}</div>
            </div>
          </template>
          <template v-else-if="column.dataIndex === '__actions__'">
            <a-button type="link" size="small" @click="openReassign(record)">
              <template #icon><EditOutlined /></template>
              {{ t('review.reassign') }}
            </a-button>
          </template>
        </template>
      </a-table>
      <a-empty
        v-if="!loading && !activeStages.length"
        :description="t('review.noActive')"
        style="padding: 40px 0"
      />
    </a-card>

    <a-modal
      v-model:open="approveOpen"
      :title="t('review.approveTitle', { name: approveTarget?.equipment_type_name || '' })"
      :confirm-loading="approveBusy"
      :ok-text="t('review.confirmSchedule')"
      :cancel-text="t('common.cancel')"
      @ok="confirmApprove"
    >
      <a-alert
        v-if="approveError"
        type="error"
        :message="approveError"
        show-icon
        style="margin-bottom: 16px"
      />
      <a-alert
        v-if="scheduleWarning"
        type="warning"
        :message="scheduleWarning"
        show-icon
        style="margin-bottom: 16px"
      />
      <a-form layout="vertical">
        <a-form-item :label="t('review.noteOrderStep')">
          <a-input
            :value="`${approveTarget?.order_no} · ${t('review.step')} ${approveTarget?.step_order}`"
            readonly
          />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item :label="t('review.scheduleStart')" required>
              <a-date-picker
                v-model:value="scheduleStart"
                show-time
                format="YYYY-MM-DD HH:mm"
                style="width: 100%"
                @change="validateSchedule"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="t('review.scheduleEnd')" required>
              <a-date-picker
                v-model:value="scheduleEnd"
                show-time
                format="YYYY-MM-DD HH:mm"
                style="width: 100%"
                @change="validateSchedule"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="t('review.assignTo')">
          <a-select
            v-model:value="assignee"
            :placeholder="t('review.unassigned')"
            allow-clear
            show-search
            option-filter-prop="label"
            :options="memberOptions"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="rejectOpen"
      :title="t('review.rejectTitle', { no: rejectTarget?.order_no || '' })"
      :ok-button-props="{ danger: true, disabled: !rejectReason.trim() }"
      :ok-text="t('review.confirmReject')"
      :cancel-text="t('common.cancel')"
      @ok="confirmReject"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('review.rejectReason')" required>
          <a-textarea
            v-model:value="rejectReason"
            :rows="4"
            :placeholder="t('review.rejectReasonPrompt')"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="reassignOpen"
      :title="t('review.reassignTitle', { no: reassignTarget?.order_no || '' })"
      :confirm-loading="reassignBusy"
      :ok-text="t('review.saveChanges')"
      :cancel-text="t('common.cancel')"
      @ok="confirmReassign"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('review.newAssignee')">
          <a-select
            v-model:value="reassignAssignee"
            :placeholder="t('review.unassigned')"
            allow-clear
            show-search
            option-filter-prop="label"
            :options="memberOptions"
          />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item :label="t('review.adjustStart')">
              <a-date-picker
                v-model:value="reassignStart"
                show-time
                format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="t('review.adjustEnd')">
              <a-date-picker
                v-model:value="reassignEnd"
                show-time
                format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="editBookingOpen"
      :title="t('review.bookingTitle', { no: editBookingTarget?.order_no || '' })"
      :confirm-loading="editBookingBusy"
      :ok-text="t('common.save')"
      :cancel-text="t('common.cancel')"
      @ok="saveBookingUpdate"
    >
      <a-alert
        v-if="editBookingError"
        type="error"
        :message="editBookingError"
        show-icon
        style="margin-bottom: 16px"
      />
      <a-descriptions :column="1" size="small">
        <a-descriptions-item :label="t('review.bookingEquipment')">
          {{ editBookingTarget?.equipment_code }}
          ({{ editBookingTarget?.equipment_type_name }})
        </a-descriptions-item>
      </a-descriptions>
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item :label="t('review.startTime')">
          <a-date-picker
            v-model:value="editBookingStart"
            show-time
            format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item :label="t('review.endTime')">
          <a-date-picker
            v-model:value="editBookingEnd"
            show-time
            format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'

const { t } = useI18n()
import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  ReloadOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { fetchStages, reviewStage } from '../../api/orders'
import { fetchBookings, updateBooking } from '../../api/scheduling'
import client from '../../api/client'
import TimelineChart from '../../components/TimelineChart.vue'

const stages = ref([])
const members = ref([])
const groupedEquipments = ref([])
const allBookings = ref([])
const loading = ref(false)

const waitingStages = computed(() => stages.value.filter((s) => s.status === 'waiting'))
const activeStages = computed(() => stages.value.filter((s) => s.status === 'in_progress'))

const memberOptions = computed(() =>
  members.value.map((u) => ({
    value: u.id,
    label: `${u.username} (${u.role})`,
  })),
)

const waitingColumns = computed(() => [
  { title: t('orders.orderNo'), dataIndex: 'order_no', width: 200 },
  { title: t('review.step'), dataIndex: 'step_order', width: 100 },
  { title: t('orders.equipmentType'), dataIndex: 'equipment_type_name' },
  { title: t('review.requester'), dataIndex: 'user_name', width: 140 },
  { title: t('orders.lotId'), dataIndex: 'lot_id', width: 120 },
  { title: '', dataIndex: '__actions__', width: 220, fixed: 'right' },
])

const activeColumns = computed(() => [
  { title: t('orders.orderNo'), dataIndex: 'order_no', width: 200 },
  { title: t('review.step'), dataIndex: 'step_order', width: 100 },
  { title: t('orders.equipmentType'), dataIndex: 'equipment_type_name', width: 160 },
  { title: t('review.assignee'), dataIndex: 'assignee_name', width: 160 },
  { title: t('orders.schedule'), dataIndex: 'schedule', width: 240 },
  { title: '', dataIndex: '__actions__', width: 140, fixed: 'right' },
])

// Approve modal state
const approveOpen = ref(false)
const approveTarget = ref(null)
const scheduleStart = ref(null)
const scheduleEnd = ref(null)
const assignee = ref(null)
const approveBusy = ref(false)
const approveError = ref('')
const scheduleWarning = ref('')

// Reject modal state
const rejectOpen = ref(false)
const rejectTarget = ref(null)
const rejectReason = ref('')

// Reassign modal state
const reassignOpen = ref(false)
const reassignTarget = ref(null)
const reassignAssignee = ref(null)
const reassignStart = ref(null)
const reassignEnd = ref(null)
const reassignBusy = ref(false)

// Booking edit modal state
const editBookingOpen = ref(false)
const editBookingTarget = ref(null)
const editBookingStart = ref(null)
const editBookingEnd = ref(null)
const editBookingBusy = ref(false)
const editBookingError = ref('')

onMounted(reloadAll)

async function reloadAll() {
  loading.value = true
  try {
    await Promise.all([loadStages(), loadMembers(), loadTimelineData()])
  } finally {
    loading.value = false
  }
}

async function loadStages() {
  const { data } = await fetchStages()
  stages.value = data.results || data || []
}

async function loadMembers() {
  const { data } = await client.get('/users/')
  members.value = (data.results || data || []).filter((u) =>
    ['lab_member', 'lab_manager'].includes(u.role),
  )
}

async function loadTimelineData() {
  const [resEq, resBk, resProf] = await Promise.all([
    client.get('/equipments/status-matrix/'),
    fetchBookings(),
    client.get('/users/profile/'),
  ])
  const myDept = resProf.data.department_name
  groupedEquipments.value = resEq.data
    .map((type) => ({
      ...type,
      equipments: type.equipments.filter((eq) => eq.department_name === myDept),
    }))
    .filter((type) => type.equipments.length > 0)
  allBookings.value = resBk.data.results || resBk.data || []
}

function openApprove(stage) {
  approveTarget.value = stage
  scheduleStart.value = null
  scheduleEnd.value = null
  assignee.value = null
  approveError.value = ''
  scheduleWarning.value = ''
  approveOpen.value = true
}

function validateSchedule() {
  scheduleWarning.value = ''
  if (scheduleStart.value && scheduleEnd.value) {
    const now = dayjs()
    if (scheduleEnd.value.isBefore(scheduleStart.value)) {
      scheduleWarning.value = t('review.endAfterStart')
    } else if (scheduleStart.value.isBefore(now)) {
      scheduleWarning.value = t('review.noPastStart')
    }
  }
}

async function confirmApprove() {
  validateSchedule()
  if (scheduleWarning.value) return
  if (!scheduleStart.value || !scheduleEnd.value) {
    approveError.value = t('review.fillTimes')
    return
  }
  approveBusy.value = true
  try {
    await reviewStage(approveTarget.value.id, {
      action: 'approve',
      schedule_start: scheduleStart.value.toISOString(),
      schedule_end: scheduleEnd.value.toISOString(),
      assignee: assignee.value,
    })
    approveOpen.value = false
    message.success(t('review.approveSuccess'))
    await Promise.all([loadStages(), loadTimelineData()])
  } catch (e) {
    approveError.value = e.response?.data?.detail || t('review.approveFailed')
  } finally {
    approveBusy.value = false
  }
}

function openReject(stage) {
  rejectTarget.value = stage
  rejectReason.value = ''
  rejectOpen.value = true
}

async function confirmReject() {
  try {
    await reviewStage(rejectTarget.value.id, {
      action: 'reject',
      rejection_reason: rejectReason.value,
    })
    rejectOpen.value = false
    message.success(t('review.rejectSuccess'))
    await loadStages()
  } catch (e) {
    message.error(e.response?.data?.detail || t('review.rejectFailed'))
  }
}

function openReassign(stage) {
  reassignTarget.value = stage
  reassignAssignee.value = stage.assignee || null
  reassignStart.value = stage.schedule_start ? dayjs(stage.schedule_start) : null
  reassignEnd.value = stage.schedule_end ? dayjs(stage.schedule_end) : null
  reassignOpen.value = true
}

async function confirmReassign() {
  if (reassignStart.value && reassignEnd.value && reassignEnd.value.isBefore(reassignStart.value)) {
    message.error(t('review.endAfterStart'))
    return
  }
  reassignBusy.value = true
  try {
    await reviewStage(reassignTarget.value.id, {
      action: 'reassign',
      assignee: reassignAssignee.value,
      schedule_start: reassignStart.value?.toISOString(),
      schedule_end: reassignEnd.value?.toISOString(),
    })
    reassignOpen.value = false
    message.success(t('review.reassignSuccess'))
    await Promise.all([loadStages(), loadTimelineData()])
  } catch (e) {
    message.error(e.response?.data?.detail || t('review.reassignFailed'))
  } finally {
    reassignBusy.value = false
  }
}

function openEditBooking(booking) {
  editBookingTarget.value = booking
  editBookingStart.value = booking.start ? dayjs(booking.start) : null
  editBookingEnd.value = booking.end ? dayjs(booking.end) : null
  editBookingError.value = ''
  editBookingOpen.value = true
}

async function saveBookingUpdate() {
  if (!editBookingStart.value || !editBookingEnd.value) {
    editBookingError.value = t('review.fillBookingTimes')
    return
  }
  if (editBookingEnd.value.isBefore(editBookingStart.value)) {
    editBookingError.value = t('review.endAfterStart')
    return
  }
  if (editBookingStart.value.isBefore(dayjs())) {
    editBookingError.value = t('review.noPastStart')
    return
  }
  editBookingBusy.value = true
  try {
    await updateBooking(editBookingTarget.value.id, {
      started_at: editBookingStart.value.toISOString(),
      ended_at: editBookingEnd.value.toISOString(),
    })
    editBookingOpen.value = false
    message.success(t('review.bookingSuccess'))
    await loadTimelineData()
  } catch (e) {
    editBookingError.value = e.response?.data?.detail || t('review.bookingFailed')
  } finally {
    editBookingBusy.value = false
  }
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}
</script>

<style scoped>
.review-page {
  padding: 0;
}
.timeline-wrapper :deep(.ant-card-body) {
  padding: 16px;
}
.muted {
  color: var(--c-text-muted);
  font-style: italic;
}
.schedule-cell {
  font-size: 12px;
  line-height: 1.6;
}
</style>
