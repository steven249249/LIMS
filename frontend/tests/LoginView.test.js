// @vitest-environment jsdom
/**
 * Component test for LoginView.
 *
 * Mounts the real component with stubbed antd elements so we focus on
 * behaviour rather than antd internals. The auth store is exercised via Pinia
 * with the network calls mocked.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createI18n } from 'vue-i18n'

vi.mock('../src/api/users', () => ({
  login: vi.fn(),
  fetchProfile: vi.fn(),
}))

import { login as apiLogin, fetchProfile } from '../src/api/users'
import LoginView from '../src/views/LoginView.vue'
import zhTW from '../src/i18n/zh-TW'

function makeI18n() {
  return createI18n({
    legacy: false,
    locale: 'zh-TW',
    fallbackLocale: 'zh-TW',
    messages: { 'zh-TW': zhTW },
  })
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Dashboard', component: { template: '<div />' } },
      { path: '/login', name: 'Login', component: LoginView },
      { path: '/register', name: 'Register', component: { template: '<div />' } },
    ],
  })
}

const STUBS = [
  'a-card', 'a-form', 'a-form-item', 'a-input', 'a-input-password',
  'a-button', 'a-divider', 'a-alert',
  'ExperimentOutlined', 'UserOutlined', 'LockOutlined',
]

describe('LoginView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('exposes a reactive form with username and password', async () => {
    // Arrange
    const router = makeRouter()
    await router.push('/login')
    const wrapper = mount(LoginView, {
      global: { plugins: [router, makeI18n()], stubs: STUBS },
    })
    // Assert — the script setup wires up a reactive form for both fields
    expect(wrapper.vm.form).toBeDefined()
    expect('username' in wrapper.vm.form).toBe(true)
    expect('password' in wrapper.vm.form).toBe(true)
  })

  it('calls auth.login when form is submitted', async () => {
    // Arrange
    apiLogin.mockResolvedValueOnce({ data: { access: 'a', refresh: 'b' } })
    fetchProfile.mockResolvedValueOnce({ data: { username: 'alice', role: 'lab_manager' } })

    const router = makeRouter()
    await router.push('/login')
    const wrapper = mount(LoginView, {
      global: { plugins: [router, makeI18n()], stubs: STUBS },
    })
    // Act — set up the reactive form state, then trigger submit
    wrapper.vm.form.username = 'alice'
    wrapper.vm.form.password = 'TestPass2026!'
    await wrapper.vm.handleLogin()
    await flushPromises()
    // Assert
    expect(apiLogin).toHaveBeenCalledWith('alice', 'TestPass2026!')
    expect(fetchProfile).toHaveBeenCalled()
  })

  it('surfaces backend error message on failure', async () => {
    // Arrange
    apiLogin.mockRejectedValueOnce({
      response: { data: { detail: '帳號密碼錯誤' } },
    })
    const router = makeRouter()
    await router.push('/login')
    const wrapper = mount(LoginView, {
      global: { plugins: [router, makeI18n()], stubs: STUBS },
    })
    // Act
    wrapper.vm.form.username = 'alice'
    wrapper.vm.form.password = 'wrong'
    await wrapper.vm.handleLogin()
    await flushPromises()
    // Assert — component-internal error state is set; antd Alert would render it
    expect(wrapper.vm.error).toBe('帳號密碼錯誤')
  })

  it('falls back to default error message when backend gives nothing useful', async () => {
    // Arrange
    apiLogin.mockRejectedValueOnce(new Error('network down'))
    const router = makeRouter()
    await router.push('/login')
    const wrapper = mount(LoginView, {
      global: { plugins: [router, makeI18n()], stubs: STUBS },
    })
    // Act
    wrapper.vm.form.username = 'a'
    wrapper.vm.form.password = 'b'
    await wrapper.vm.handleLogin()
    await flushPromises()
    // Assert
    expect(wrapper.vm.error).toContain('登入失敗')
  })
})
