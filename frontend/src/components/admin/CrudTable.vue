<template>
  <div class="crud-page">
    <a-page-header
      :title="title"
      :sub-title="subtitle"
      class="crud-header"
      :back-icon="false"
    >
      <template #extra>
        <slot name="extra-actions" :selected-row-keys="selectedRowKeys" :reload="loadData" />
        <a-input-search
          v-model:value="searchText"
          :placeholder="searchPlaceholder || t('crud.searchPlaceholder')"
          allow-clear
          style="width: 280px"
          @search="onSearch"
        />
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          {{ t('crud.new') }}
        </a-button>
        <a-button @click="loadData">
          <template #icon><ReloadOutlined /></template>
          {{ t('crud.refresh') }}
        </a-button>
      </template>
    </a-page-header>

    <a-table
      :columns="tableColumns"
      :data-source="rows"
      :row-key="rowKey"
      :loading="loading"
      :pagination="pagination"
      :row-selection="selectable ? rowSelectionConfig : undefined"
      bordered
      size="middle"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === '__actions__'">
          <a-space>
            <a-button size="small" type="link" @click="openEdit(record)">
              <template #icon><EditOutlined /></template>
              {{ t('crud.edit') }}
            </a-button>
            <a-popconfirm
              :title="t('crud.confirmDelete', { label: resourceLabel })"
              :ok-text="t('crud.okText')"
              ok-type="danger"
              :cancel-text="t('crud.cancel')"
              @confirm="onDelete(record)"
            >
              <a-button size="small" type="link" danger>
                <template #icon><DeleteOutlined /></template>
                {{ t('crud.delete') }}
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
        <template v-else-if="column.customSlot === 'tag'">
          <a-tag :color="tagColor(record[column.dataIndex])">
            {{ record[column.dataIndex] }}
          </a-tag>
        </template>
        <template v-else-if="column.customSlot === 'datetime'">
          {{ formatDate(record[column.dataIndex]) }}
        </template>
        <template v-else-if="column.customSlot === 'boolean'">
          <a-tag :color="record[column.dataIndex] ? 'success' : 'default'">
            {{ record[column.dataIndex] ? '是' : '否' }}
          </a-tag>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalOpen"
      :title="modalTitle"
      :confirm-loading="submitting"
      width="640px"
      :mask-closable="false"
      :ok-text="t('crud.save')"
      :cancel-text="t('crud.cancel')"
      @ok="onSubmit"
      @cancel="modalOpen = false"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :label-col="{ span: 7 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-row :gutter="0">
          <a-col
            v-for="field in visibleFields"
            :key="field.name"
            :span="field.span || 24"
          >
            <a-form-item
              :name="field.name"
              :label="field.label"
              :rules="resolveRules(field)"
            >
              <component
                :is="fieldComponent(field)"
                v-bind="fieldBind(field)"
                v-model:value="formState[field.name]"
              >
                <template v-if="field.type === 'select'">
                  <a-select-option
                    v-for="opt in resolvedOptions(field)"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </a-select-option>
                </template>
              </component>
              <div v-if="field.help" class="field-help">{{ field.help }}</div>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'

const { t } = useI18n()

const props = defineProps({
  resource: { type: Object, required: true },
  resourceLabel: { type: String, default: '紀錄' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  columns: { type: Array, required: true },
  formFields: { type: Array, required: true },
  rowKey: { type: String, default: 'id' },
  searchPlaceholder: { type: String, default: '搜尋...' },
  defaultOrdering: { type: String, default: '' },
  /**
   * Map of field-name → resolved option list. Pre-loaded options bypass the
   * per-field optionsResource fetch (useful when the same lookup is shared
   * across many fields on the page).
   */
  presetOptions: { type: Object, default: () => ({}) },
  /** When true, the table renders a leading checkbox column and emits
   *  `update:selectedRowKeys` so the parent can drive bulk operations. */
  selectable: { type: Boolean, default: false },
})

const emit = defineEmits(['update:selectedRowKeys'])

const rows = ref([])
const loading = ref(false)
const searchText = ref('')
const ordering = ref(props.defaultOrdering)

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50', '100'],
  showTotal: (total) => t('crud.paginationTotal', { total }),
})

const modalOpen = ref(false)
const editingId = ref(null)
const selectedRowKeys = ref([])

const rowSelectionConfig = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys) => {
    selectedRowKeys.value = keys
    emit('update:selectedRowKeys', keys)
  },
}))

function clearSelection() {
  selectedRowKeys.value = []
  emit('update:selectedRowKeys', [])
}
const formState = reactive({})
const formRef = ref(null)
const submitting = ref(false)

// Per-field dynamically loaded option lists (e.g. department dropdowns)
const dynamicOptions = reactive({})

const isEditing = computed(() => editingId.value !== null)
const modalTitle = computed(() =>
  isEditing.value
    ? t('crud.editingTitle', { label: props.resourceLabel })
    : t('crud.addingTitle', { label: props.resourceLabel }),
)

const tableColumns = computed(() => [
  ...props.columns,
  { title: t('crud.actions'), dataIndex: '__actions__', width: 160, fixed: 'right' },
])

const visibleFields = computed(() =>
  props.formFields.filter((f) =>
    isEditing.value ? !f.hideOnUpdate : !f.hideOnCreate,
  ),
)

onMounted(() => {
  loadData()
  preloadDynamicOptions()
})

async function preloadDynamicOptions() {
  for (const field of props.formFields) {
    if (field.optionsResource && !props.presetOptions[field.name]) {
      try {
        const { data } = await field.optionsResource.list({ page_size: 200 })
        dynamicOptions[field.name] = (data.results || []).map((row) => ({
          value: row[field.optionValue || 'id'],
          label: row[field.optionLabel] ?? row.name ?? row.id,
        }))
      } catch (e) {
        console.warn(`Failed to load options for field "${field.name}"`, e)
        dynamicOptions[field.name] = []
      }
    }
  }
}

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    if (searchText.value) params.search = searchText.value
    if (ordering.value) params.ordering = ordering.value
    const { data } = await props.resource.list(params)
    rows.value = data.results || []
    pagination.total = data.count || 0
  } catch (e) {
    handleApiError(e, t('crud.loadFailed'))
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.current = 1
  loadData()
}

function onTableChange(pag, _filters, sorter) {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  if (sorter && sorter.field) {
    const dir = sorter.order === 'descend' ? '-' : ''
    ordering.value = sorter.order ? `${dir}${sorter.field}` : props.defaultOrdering
  }
  loadData()
}

function openCreate() {
  editingId.value = null
  Object.keys(formState).forEach((k) => delete formState[k])
  for (const field of props.formFields) {
    formState[field.name] = field.defaultValue ?? defaultValueByType(field.type)
  }
  modalOpen.value = true
}

function openEdit(record) {
  editingId.value = record[props.rowKey]
  Object.keys(formState).forEach((k) => delete formState[k])
  for (const field of props.formFields) {
    if (field.writeOnly) {
      formState[field.name] = ''
    } else {
      formState[field.name] = record[field.name] ?? defaultValueByType(field.type)
    }
  }
  modalOpen.value = true
}

function defaultValueByType(type) {
  if (type === 'switch') return false
  if (type === 'number') return null
  return ''
}

async function onSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload = buildPayload()
    if (isEditing.value) {
      await props.resource.update(editingId.value, payload)
      message.success(t('crud.updatedSuccess', { label: props.resourceLabel }))
    } else {
      await props.resource.create(payload)
      message.success(t('crud.addedSuccess', { label: props.resourceLabel }))
    }
    modalOpen.value = false
    loadData()
  } catch (e) {
    handleApiError(e, t('crud.addFailed'))
  } finally {
    submitting.value = false
  }
}

function buildPayload() {
  const payload = {}
  for (const field of props.formFields) {
    if (field.hideOnUpdate && isEditing.value) continue
    if (field.hideOnCreate && !isEditing.value) continue

    let value = formState[field.name]
    // Skip empty writeOnly fields on update (don't reset password)
    if (field.writeOnly && isEditing.value && (value === '' || value == null)) continue
    // Convert empty strings on optional FK selects to null for backend
    if (field.nullableEmpty && (value === '' || value == null)) value = null
    payload[field.name] = value
  }
  return payload
}

async function onDelete(record) {
  try {
    await props.resource.remove(record[props.rowKey])
    message.success(t('crud.deletedSuccess', { label: props.resourceLabel }))
    if (rows.value.length === 1 && pagination.current > 1) {
      pagination.current -= 1
    }
    loadData()
  } catch (e) {
    handleApiError(e, t('crud.deleteFailed'))
  }
}

function handleApiError(error, fallback) {
  const data = error?.response?.data
  let detail = fallback
  if (typeof data === 'string') detail = data
  else if (data?.detail) detail = data.detail
  else if (data && typeof data === 'object') {
    const firstKey = Object.keys(data)[0]
    const firstValue = data[firstKey]
    detail = `${firstKey}: ${Array.isArray(firstValue) ? firstValue.join(', ') : firstValue}`
  }
  message.error(detail)
}

function fieldComponent(field) {
  switch (field.type) {
    case 'textarea':
      return 'a-textarea'
    case 'number':
      return 'a-input-number'
    case 'password':
      return 'a-input-password'
    case 'select':
      return 'a-select'
    case 'switch':
      return 'a-switch'
    case 'datetime':
      return DateTimePicker
    default:
      return 'a-input'
  }
}

function fieldBind(field) {
  const base = { placeholder: field.placeholder || field.label }
  if (field.type === 'textarea') return { ...base, rows: 3 }
  if (field.type === 'number') return { ...base, style: { width: '100%' } }
  if (field.type === 'select') {
    return {
      ...base,
      allowClear: !!field.nullableEmpty,
      showSearch: true,
      optionFilterProp: 'children',
      style: { width: '100%' },
    }
  }
  if (field.type === 'switch') return {}
  if (field.type === 'datetime') return { style: { width: '100%' } }
  return base
}

function resolvedOptions(field) {
  if (props.presetOptions[field.name]) return props.presetOptions[field.name]
  if (field.options) return field.options
  return dynamicOptions[field.name] || []
}

function resolveRules(field) {
  if (field.rules) return field.rules
  const rules = []
  if (field.required && !(field.writeOnly && isEditing.value)) {
    rules.push({ required: true, message: t('crud.requiredField', { label: field.label }) })
  }
  if (field.type === 'password' && !field.writeOnly) {
    rules.push({ min: 8, message: t('crud.minPassword') })
  }
  return rules
}

function tagColor(value) {
  const palette = {
    available: 'success', occupied: 'warning', maintenance: 'error',
    pending: 'default', inactive: 'default',
    active: 'success', suspended: 'error',
    waiting: 'warning', in_progress: 'processing', done: 'success',
    rejected: 'error', created: 'default',
    superuser: 'red', lab_manager: 'geekblue', lab_member: 'cyan',
    regular_employee: 'default',
    GET: 'blue', POST: 'green', PATCH: 'orange', PUT: 'orange', DELETE: 'red',
    login: 'cyan', logout: 'default', create: 'green', read: 'blue',
    update: 'orange', delete: 'red',
  }
  return palette[value] || 'default'
}

function formatDate(value) {
  if (!value) return '—'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

// Inline DatePicker wrapper that converts ISO strings <-> dayjs
const DateTimePicker = {
  props: ['value'],
  emits: ['update:value'],
  setup(p, { emit }) {
    return () =>
      h('a-date-picker', {
        value: p.value ? dayjs(p.value) : null,
        showTime: true,
        format: 'YYYY-MM-DD HH:mm:ss',
        style: { width: '100%' },
        'onUpdate:value': (v) => emit('update:value', v ? v.toISOString() : null),
      })
  },
}

watch(
  () => props.defaultOrdering,
  (val) => {
    ordering.value = val
  },
)

defineExpose({ reload: loadData, clearSelection })
</script>

<style scoped>
.crud-page {
  padding: 0;
}
.crud-header {
  padding: 0 0 16px;
}
.crud-header :deep(.ant-page-header-heading-extra) {
  display: flex;
  gap: 12px;
}
.field-help {
  color: var(--c-text-muted);
  font-size: 12px;
  line-height: 1.4;
  margin-top: 2px;
}
</style>
