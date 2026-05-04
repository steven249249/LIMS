<template>
  <div class="auth-stage">
    <div class="auth-bg-blob auth-bg-blob--purple"></div>
    <div class="auth-bg-blob auth-bg-blob--blue"></div>

    <a-card class="auth-card" :bordered="false">
      <div class="auth-brand">
        <UserAddOutlined class="brand-icon" />
        <h1 class="brand-title">{{ t('auth.register') }}</h1>
        <p class="brand-subtitle">{{ t('auth.registerSubtitle') }}</p>
      </div>

      <a-result
        v-if="success"
        status="success"
        :title="t('auth.registerSuccess')"
        :sub-title="t('auth.registerSuccessSubtitle')"
      >
        <template #extra>
          <router-link to="/login">
            <a-button type="primary" size="large">{{ t('auth.login') }}</a-button>
          </router-link>
        </template>
      </a-result>

      <a-form
        v-else
        :model="form"
        layout="vertical"
        @finish="handleRegister"
      >
        <a-form-item
          :label="t('auth.username')"
          name="username"
          :rules="[
            { required: true, message: t('auth.loginPrompt') },
            { min: 3, message: t('auth.minUsername') },
          ]"
        >
          <a-input v-model:value="form.username">
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item
          :label="t('auth.email')"
          name="email"
          :rules="[
            { required: true, type: 'email', message: t('auth.requireEmail') },
          ]"
        >
          <a-input v-model:value="form.email" placeholder="example@lims.local">
            <template #prefix><MailOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item
          :label="t('auth.password')"
          name="password"
          :rules="[
            { required: true, message: t('auth.passwordPrompt') },
            { min: 8, message: t('auth.minPassword') },
          ]"
        >
          <a-input-password v-model:value="form.password" :placeholder="t('auth.minPassword')">
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>

        <a-form-item
          :label="t('auth.fullName')"
          name="first_name"
          :rules="[{ required: true, message: t('auth.fullName') }]"
        >
          <a-input v-model:value="form.first_name" />
        </a-form-item>

        <a-form-item :label="t('auth.role')" name="role">
          <a-select v-model:value="form.role" :options="roleOptions" />
        </a-form-item>

        <a-alert
          v-if="error"
          type="error"
          :message="error"
          show-icon
          banner
          style="margin-bottom: 16px"
        />

        <a-button
          type="primary"
          html-type="submit"
          :loading="loading"
          block
          size="large"
        >
          {{ t('auth.submit') }}
        </a-button>

        <div class="back-link">
          {{ t('auth.haveAccount') }}
          <router-link to="/login">{{ t('auth.backToLogin') }}</router-link>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  LockOutlined,
  MailOutlined,
  UserAddOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import client from '../api/client'

const { t } = useI18n()

const form = reactive({
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'regular_employee',
})

const roleOptions = computed(() => [
  { value: 'regular_employee', label: t('roles.regular_employee') },
  { value: 'lab_manager', label: t('roles.lab_manager') },
  { value: 'lab_member', label: t('roles.lab_member') },
])

const loading = ref(false)
const error = ref('')
const success = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await client.post('/users/register/', form)
    success.value = true
  } catch (e) {
    const data = e.response?.data
    if (typeof data === 'string') error.value = data
    else if (data?.detail) error.value = data.detail
    else if (data && typeof data === 'object') {
      const k = Object.keys(data)[0]
      error.value = `${k}: ${Array.isArray(data[k]) ? data[k].join(', ') : data[k]}`
    } else error.value = t('auth.registerFailed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-stage {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 24px 0;
  background: linear-gradient(135deg, #eff6ff 0%, #ede9fe 100%);
}
.auth-bg-blob {
  position: absolute;
  width: 480px;
  height: 480px;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
  pointer-events: none;
}
.auth-bg-blob--purple {
  background: #a78bfa;
  top: -100px;
  left: -120px;
}
.auth-bg-blob--blue {
  background: #60a5fa;
  bottom: -120px;
  right: -120px;
}
.auth-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}
.auth-brand {
  text-align: center;
  margin-bottom: 24px;
}
.brand-icon {
  font-size: 40px;
  color: #1890ff;
  margin-bottom: 8px;
}
.brand-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 4px;
  background: linear-gradient(135deg, #1890ff, #722ed1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.brand-subtitle {
  margin: 0;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.back-link {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}
</style>
