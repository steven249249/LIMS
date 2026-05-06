<template>
  <CrudTable
    :resource="adminWaferLots"
    :resource-label="t('admin.pages.waferLots.label')"
    :title="t('admin.pages.waferLots.title')"
    :subtitle="t('admin.pages.waferLots.subtitle')"
    :search-placeholder="t('admin.pages.waferLots.search')"
    default-ordering="code"
    :columns="columns"
    :form-fields="formFields"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CrudTable from '../../components/admin/CrudTable.vue'
import { adminWaferLots, adminFabs } from '../../api/admin'

const { t } = useI18n()

const columns = computed(() => [
  { title: t('admin.pages.waferLots.code'), dataIndex: 'code', sorter: true, width: 220 },
  { title: 'FAB', dataIndex: 'fab_name', width: 160 },
  { title: t('admin.pages.waferLots.notes'), dataIndex: 'notes', ellipsis: true },
])

const formFields = computed(() => [
  {
    name: 'code',
    label: t('admin.pages.waferLots.code'),
    type: 'text',
    required: true,
    placeholder: 'LOT-2026-A001',
  },
  {
    name: 'fab',
    label: 'FAB',
    type: 'select',
    required: true,
    optionsResource: adminFabs,
    optionLabel: 'fab_name',
  },
  { name: 'notes', label: t('admin.pages.waferLots.notes'), type: 'textarea' },
])
</script>
