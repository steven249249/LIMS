// @vitest-environment jsdom
/**
 * Unit tests for the auth Pinia store.
 *
 * The api/users module is mocked so we never hit the network — pure unit-level
 * verification of the store's contract: token persistence, profile loading,
 * computed roles, and logout cleanup.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../src/api/users', () => ({
  login: vi.fn(),
  fetchProfile: vi.fn(),
}))

import { login as apiLogin, fetchProfile } from '../src/api/users'
import { useAuthStore } from '../src/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts logged out with empty user', () => {
    // Arrange
    const auth = useAuthStore()
    // Assert
    expect(auth.user).toBeNull()
    expect(auth.accessToken).toBe('')
    expect(auth.isLoggedIn).toBe(false)
  })

  it('login() persists tokens and loads profile', async () => {
    // Arrange
    apiLogin.mockResolvedValueOnce({
      data: { access: 'access-1', refresh: 'refresh-1' },
    })
    fetchProfile.mockResolvedValueOnce({
      data: { username: 'alice', role: 'lab_manager', email: 'a@b.c' },
    })
    const auth = useAuthStore()
    // Act
    await auth.login('alice', 'pwd')
    // Assert
    expect(auth.accessToken).toBe('access-1')
    expect(auth.refreshToken).toBe('refresh-1')
    expect(localStorage.getItem('access_token')).toBe('access-1')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1')
    expect(auth.user.username).toBe('alice')
    expect(auth.role).toBe('lab_manager')
  })

  it('logout() clears state and storage', () => {
    // Arrange
    const auth = useAuthStore()
    auth.accessToken = 'a'
    auth.refreshToken = 'b'
    auth.user = { username: 'x' }
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('refresh_token', 'b')
    // Act
    auth.logout()
    // Assert
    expect(auth.user).toBeNull()
    expect(auth.accessToken).toBe('')
    expect(auth.refreshToken).toBe('')
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('logout() runs when fetchProfile fails', async () => {
    // Arrange
    apiLogin.mockResolvedValueOnce({ data: { access: 'a', refresh: 'b' } })
    fetchProfile.mockRejectedValueOnce(new Error('401'))
    const auth = useAuthStore()
    // Act — login should still complete but profile load fails internally
    await auth.login('alice', 'pwd')
    // Assert — logout was triggered, tokens cleared
    expect(auth.user).toBeNull()
    expect(auth.accessToken).toBe('')
  })

  describe('role computeds', () => {
    it.each([
      ['superuser', { isManager: true, isMember: true, isSuperuser: true }],
      ['lab_manager', { isManager: true, isMember: true, isSuperuser: false }],
      ['lab_member', { isManager: false, isMember: true, isSuperuser: false }],
      ['regular_employee', { isManager: false, isMember: false, isSuperuser: false }],
    ])('role=%s exposes correct flags', (role, expected) => {
      // Arrange
      const auth = useAuthStore()
      auth.user = { username: 'x', role }
      // Assert
      expect(auth.isManager).toBe(expected.isManager)
      expect(auth.isMember).toBe(expected.isMember)
      expect(auth.isSuperuser).toBe(expected.isSuperuser)
    })

    it('isSuperuser is also true when is_superuser flag is set without role', () => {
      const auth = useAuthStore()
      auth.user = { username: 'x', role: 'lab_manager', is_superuser: true }
      expect(auth.isSuperuser).toBe(true)
    })
  })
})
