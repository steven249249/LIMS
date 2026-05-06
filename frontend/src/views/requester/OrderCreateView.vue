<template>
  <div class="create-page">
    <a-page-header
      :title="t('createOrder.title')"
      :sub-title="t('createOrder.subtitle')"
      :back-icon="false"
    />

    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :lg="14">
        <a-card :bordered="false" :title="t('createOrder.formTitle')">
          <a-result
            v-if="success"
            status="success"
            :title="t('createOrder.successTitle', { orderNo: createdOrderNo })"
            :sub-title="t('createOrder.successSub')"
          >
            <template #extra>
              <a-button type="primary" @click="resetForm">{{ t('createOrder.continueSubmit') }}</a-button>
              <a-button @click="$router.push('/orders')">{{ t('createOrder.seeOrderList') }}</a-button>
            </template>
          </a-result>

          <a-form
            v-else
            :model="form"
            layout="vertical"
            @finish="handleSubmit"
          >
            <a-form-item
              :label="t('createOrder.targetLabLabel')"
              name="target_department"
              :rules="[{ required: true, message: t('createOrder.requireTargetLab') }]"
            >
              <a-select
                v-model:value="form.target_department"
                :placeholder="t('createOrder.targetLabPlaceholder')"
                show-search
                option-filter-prop="label"
                size="large"
                :options="labOptions"
                @change="onLabChange"
              />
            </a-form-item>

            <a-form-item
              :label="t('createOrder.equipmentTypeLabel')"
              name="equipment_type"
              :rules="[{ required: true, message: t('createOrder.requireEquipmentType') }]"
            >
              <a-select
                v-model:value="form.equipment_type"
                :placeholder="form.target_department ? t('createOrder.equipmentTypePlaceholder') : t('createOrder.pickLabFirst')"
                show-search
                option-filter-prop="label"
                size="large"
                :options="equipmentTypeOptions"
                :disabled="!form.target_department"
              />
            </a-form-item>

            <a-form-item :label="t('createOrder.lotIdLabel')" name="lot_id">
              <a-input
                v-model:value="form.lot_id"
                :placeholder="t('createOrder.lotIdPlaceholder')"
                size="large"
              />
            </a-form-item>

            <a-form-item name="is_urgent">
              <a-checkbox v-model:checked="form.is_urgent">
                <a-tag color="red" style="margin-right: 6px">{{ t('orders.urgent') }}</a-tag>
                {{ t('createOrder.urgentCheckbox') }}
              </a-checkbox>
            </a-form-item>

            <a-form-item :label="t('orders.remark')" name="remark">
              <a-textarea
                v-model:value="form.remark"
                :rows="3"
                :placeholder="t('createOrder.remarkPlaceholder')"
              />
            </a-form-item>

            <a-alert
              type="info"
              show-icon
              :message="t('createOrder.singleLabNote')"
              style="margin-bottom: 16px"
            />

            <a-alert
              v-if="error"
              type="error"
              show-icon
              :message="error"
              style="margin-bottom: 16px"
            />

            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              size="large"
            >
              <template #icon><SendOutlined /></template>
              {{ t('createOrder.submitButton') }}
            </a-button>
          </a-form>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="10">
        <a-card :bordered="false" :title="t('createOrder.targetLabPreview')" class="side-card">
          <a-empty
            v-if="!form.target_department"
            :description="t('createOrder.pickLabHint')"
          />
          <template v-else>
            <a-descriptions :column="1" size="small">
              <a-descriptions-item :label="t('createOrder.targetLabLabel')">
                <span class="font-bold">{{ selectedLabName }}</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('createOrder.availableTypes')">
                <a-space wrap>
                  <a-tag
                    v-for="t in equipmentTypesAtLab"
                    :key="t.id"
                    :color="t.id === form.equipment_type ? 'blue' : 'default'"
                  >
                    {{ t.name }}
                  </a-tag>
                </a-space>
              </a-descriptions-item>
            </a-descriptions>

            <a-divider style="margin: 12px 0" />

            <div v-if="form.equipment_type">
              <div class="muted" style="margin-bottom: 6px">
                {{ t('createOrder.unitsAtLab') }}
              </div>
              <a-list
                :data-source="unitsForSelected"
                size="small"
              >
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-space>
                      <a-tag :color="item.status === 'available' ? 'success' : 'warning'">
                        {{ item.status }}
                      </a-tag>
                      <span class="font-bold">{{ item.code }}</span>
                    </a-space>
                  </a-list-item>
                </template>
              </a-list>
            </div>
          </template>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { SendOutlined } from '@ant-design/icons-vue'
import { fetchEquipments } from '../../api/equipments'
import { createOrder } from '../../api/orders'

const { t } = useI18n()

const equipments = ref([])
const loading = ref(false)
const error = ref('')
const success = ref(false)
const createdOrderNo = ref(null)

const form = reactive({
  target_department: undefined,
  equipment_type: undefined,
  is_urgent: false,
  lot_id: '',
  remark: '',
})

// Group equipments by department for the lab dropdown.
const labOptions = computed(() => {
  const map = new Map()
  for (const eq of equipments.value) {
    if (!eq.department) continue
    if (!map.has(eq.department)) {
      map.set(eq.department, eq.department_name || eq.department)
    }
  }
  return Array.from(map.entries()).map(([id, name]) => ({ value: id, label: name }))
})

const selectedLabName = computed(() => {
  const opt = labOptions.value.find((o) => o.value === form.target_department)
  return opt?.label || ''
})

// Equipment types available within the picked lab (deduped by type id).
const equipmentTypesAtLab = computed(() => {
  if (!form.target_department) return []
  const seen = new Map()
  for (const eq of equipments.value) {
    if (eq.department !== form.target_department) continue
    if (!seen.has(eq.equipment_type)) {
      seen.set(eq.equipment_type, { id: eq.equipment_type, name: eq.type_name })
    }
  }
  return Array.from(seen.values())
})

const equipmentTypeOptions = computed(() =>
  equipmentTypesAtLab.value.map((t) => ({ value: t.id, label: t.name })),
)

const unitsForSelected = computed(() =>
  equipments.value.filter(
    (eq) =>
      eq.department === form.target_department &&
      eq.equipment_type === form.equipment_type,
  ),
)

onMounted(async () => {
  try {
    const { data } = await fetchEquipments()
    equipments.value = data.results || data
  } catch {
    message.error(t('createOrder.loadEquipmentsFailed'))
  }
})

function onLabChange() {
  // Reset the type when the lab changes — types are scoped to the picked lab.
  form.equipment_type = undefined
}

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    const payload = {
      target_department: form.target_department,
      equipment_type: form.equipment_type,
      is_urgent: form.is_urgent,
      lot_id: form.lot_id,
      remark: form.remark,
    }
    const { data } = await createOrder(payload)
    createdOrderNo.value = data.order_no
    success.value = true
    message.success(t('createOrder.successTitle', { orderNo: data.order_no }))
  } catch (e) {
    const data = e.response?.data
    if (typeof data === 'string') error.value = data
    else if (data?.detail) error.value = data.detail
    else if (data && typeof data === 'object') {
      const k = Object.keys(data)[0]
      error.value = `${k}: ${Array.isArray(data[k]) ? data[k].join(', ') : data[k]}`
    } else error.value = t('createOrder.submitFailed')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.target_department = undefined
  form.equipment_type = undefined
  form.is_urgent = false
  form.lot_id = ''
  form.remark = ''
  success.value = false
  createdOrderNo.value = null
}
</script>

<style scoped>
.create-page {
  padding: 0;
}
.muted {
  color: var(--c-text-muted);
  font-size: 12px;
}
.font-bold {
  font-weight: 600;
}
.side-card :deep(.ant-card-body) {
  padding: 12px 16px;
}
</style>
