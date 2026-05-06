<template>
  <CrudTable
    :resource="adminExperiments"
    :resource-label="t('admin.pages.experiments.label')"
    :title="t('admin.pages.experiments.title')"
    :subtitle="t('admin.pages.experiments.subtitle')"
    :search-placeholder="t('admin.pages.experiments.search')"
    default-ordering="name"
    :columns="columns"
    :form-fields="formFields"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CrudTable from '../../components/admin/CrudTable.vue'
import { adminDepartments, adminExperiments } from '../../api/admin'

const { t } = useI18n()

const columns = computed(() => [
  { title: t('orders.experiment'), dataIndex: 'name', sorter: true, width: 240 },
  { title: t('admin.pages.departments.label'), dataIndex: 'department_name', width: 200 },
  { title: t('orders.remark'), dataIndex: 'remark', ellipsis: true },
])

const formFields = computed(() => [
  { name: 'name', label: t('orders.experiment'), type: 'text', required: true,
    placeholder: 'SEM-Inspection-01' },
  {
    name: 'department',
    label: t('admin.pages.departments.label'),
    type: 'select',
    required: true,
    optionsResource: adminDepartments,
    optionLabel: 'name',
  },
  { name: 'remark', label: t('orders.remark'), type: 'textarea' },
])
</script>
