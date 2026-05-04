<template>
  <div class="auth-stage">
    <div class="auth-bg-blob auth-bg-blob--purple"></div>
    <div class="auth-bg-blob auth-bg-blob--blue"></div>

    <a-card class="auth-card" :bordered="false">
      <div class="auth-brand">
        <ExperimentOutlined class="brand-icon" />
        <h1 class="brand-title">{{ t('common.appName') }}</h1>
        <p class="brand-subtitle">{{ t('common.appSubtitle') }}</p>
      </div>

      <a-form
        :model="form"
        layout="vertical"
        autocomplete="on"
        @finish="handleLogin"
      >
        <a-form-item
          :label="t('auth.username')"
          name="username"
          :rules="[{ required: true, message: t('auth.loginPrompt') }]"
        >
          <a-input
            v-model:value="form.username"
            size="large"
            :placeholder="t('auth.loginPrompt')"
            autocomplete="username"
          >
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item
          :label="t('auth.password')"
          name="password"
          :rules="[{ required: true, message: t('auth.passwordPrompt') }]"
        >
          <a-input-password
            v-model:value="form.password"
            size="large"
            :placeholder="t('auth.passwordPrompt')"
            autocomplete="current-password"
          >
            <template #prefix><LockOutlined /></template>
          </a-input-password>
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
          {{ t('auth.login') }}
        </a-button>
      </a-form>

      <a-divider plain style="margin: 24px 0 16px; color: rgba(0, 0, 0, 0.35)">
        {{ t('auth.noAccount') }}
      </a-divider>

      <router-link to="/register">
        <a-button block size="large">{{ t('auth.register') }}</a-button>
      </router-link>
    </a-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ExperimentOutlined,
  LockOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || t('auth.loginFailed')
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
  max-width: 420px;
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
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #1890ff, #722ed1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 4px;
}
.brand-subtitle {
  margin: 0;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  letter-spacing: 0.6px;
  text-transform: uppercase;
}
</style>
