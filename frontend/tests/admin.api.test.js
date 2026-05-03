/**
 * Unit tests for the admin API client wrapper.
 *
 * We mock the underlying axios instance (api/client.js) so each resource's
 * URL shape and HTTP verb are verified without making real network calls.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import client from '../src/api/client'
import {
  adminEquipmentTypes,
  adminFabs,
  adminUsers,
  fetchActivityLogs,
  fetchAdminDashboard,
} from '../src/api/admin'

describe('admin api resources', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('adminFabs', () => {
    it('list() forwards query params', () => {
      adminFabs.list({ search: 'FAB12' })
      expect(client.get).toHaveBeenCalledWith('/admin/fabs/', {
        params: { search: 'FAB12' },
      })
    })

    it('retrieve() hits item URL', () => {
      adminFabs.retrieve('uuid-abc')
      expect(client.get).toHaveBeenCalledWith('/admin/fabs/uuid-abc/')
    })

    it('create() sends POST with payload', () => {
      adminFabs.create({ fab_name: 'F2' })
      expect(client.post).toHaveBeenCalledWith('/admin/fabs/', { fab_name: 'F2' })
    })

    it('update() sends PATCH with id and payload', () => {
      adminFabs.update('uuid-abc', { fab_name: 'F3' })
      expect(client.patch).toHaveBeenCalledWith('/admin/fabs/uuid-abc/', {
        fab_name: 'F3',
      })
    })

    it('remove() sends DELETE on item URL', () => {
      adminFabs.remove('uuid-abc')
      expect(client.delete).toHaveBeenCalledWith('/admin/fabs/uuid-abc/')
    })
  })

  it('adminUsers points at /admin/users/', () => {
    adminUsers.list()
    expect(client.get).toHaveBeenCalledWith('/admin/users/', { params: {} })
  })

  it('adminEquipmentTypes points at /admin/equipment-types/', () => {
    adminEquipmentTypes.list()
    expect(client.get).toHaveBeenCalledWith('/admin/equipment-types/', {
      params: {},
    })
  })

  it('fetchAdminDashboard reads monitoring/dashboard', () => {
    fetchAdminDashboard()
    expect(client.get).toHaveBeenCalledWith('/monitoring/dashboard/')
  })

  it('fetchActivityLogs forwards filter params', () => {
    fetchActivityLogs({ action_type: 'login', page: 2 })
    expect(client.get).toHaveBeenCalledWith('/monitoring/logs/', {
      params: { action_type: 'login', page: 2 },
    })
  })
})
