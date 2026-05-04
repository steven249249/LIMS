<template>
  <CrudTable
    :resource="adminEquipment"
    resource-label="設備"
    title="設備"
    subtitle="管理員的主要任務:把每台設備分配給對應的實驗室 (department)"
    search-placeholder="依設備代碼或類型搜尋"
    default-ordering="code"
    :columns="columns"
    :form-fields="formFields"
  />
</template>

<script setup>
import { h } from 'vue'
import { Tag } from 'ant-design-vue'
import CrudTable from '../../components/admin/CrudTable.vue'
import {
  adminDepartments,
  adminEquipment,
  adminEquipmentTypes,
} from '../../api/admin'

const statusOptions = [
  { value: 'available', label: '可用' },
  { value: 'occupied', label: '占用中' },
  { value: 'pending', label: '待處理' },
  { value: 'maintenance', label: '維修' },
  { value: 'inactive', label: '停用' },
]
const statusColor = {
  available: 'success', occupied: 'warning',
  pending: 'default', maintenance: 'error', inactive: 'default',
}

const columns = [
  { title: '設備代碼', dataIndex: 'code', sorter: true, width: 160 },
  { title: '類型', dataIndex: 'equipment_type_name', width: 160 },
  { title: '所屬部門', dataIndex: 'department_name', width: 160,
    customRender: ({ value }) => value || '—' },
  { title: '狀態', dataIndex: 'status', width: 120, sorter: true,
    customRender: ({ value }) =>
      h(Tag, { color: statusColor[value] || 'default' }, () =>
        statusOptions.find((o) => o.value === value)?.label || value,
      ),
  },
]

const formFields = [
  { name: 'equipment_type', label: '設備類型', type: 'select', required: true,
    optionsResource: adminEquipmentTypes, optionLabel: 'name', span: 12 },
  { name: 'department', label: '分配實驗室', type: 'select', required: true,
    optionsResource: adminDepartments, optionLabel: 'name', span: 12,
    help: '每台設備必須屬於一間實驗室 — 這是後台分配機台的主要操作' },
  { name: 'code', label: '設備代碼', type: 'text', required: true,
    placeholder: '例如: SEM-001', span: 12 },
  { name: 'status', label: '狀態', type: 'select', required: true,
    options: statusOptions, defaultValue: 'available', span: 12 },
]
</script>
