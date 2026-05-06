/**
 * src/api/admin.js — Superuser-only admin endpoints.
 *
 * Each domain table is wrapped in a uniform CRUD resource so the generic
 * CrudTable component can drive any table without bespoke API plumbing.
 */
import client from './client'

const resource = (path) => ({
  /** List with optional query params (search, ordering, page, page_size). */
  list: (params = {}) => client.get(`/admin/${path}/`, { params }),
  /** Retrieve a single record by id. */
  retrieve: (id) => client.get(`/admin/${path}/${id}/`),
  /** Create a new record. */
  create: (data) => client.post(`/admin/${path}/`, data),
  /** Partial update (PATCH semantics). */
  update: (id, data) => client.patch(`/admin/${path}/${id}/`, data),
  /** Delete a record. */
  remove: (id) => client.delete(`/admin/${path}/${id}/`),
})

export const adminFabs = resource('fabs')
export const adminDepartments = resource('departments')
export const adminWaferLots = resource('wafer-lots')
export const adminUsers = {
  ...resource('users'),
  /** Provision N requesters / lab members / lab managers in one shot. */
  bulkCreate: (payload) => client.post('/admin/users/bulk-create/', payload),
  /** Delete N user accounts; safety rails on backend skip self/last superuser. */
  bulkDelete: (ids) => client.post('/admin/users/bulk-delete/', { ids }),
}
export const adminExperiments = resource('experiments')
export const adminEquipmentTypes = resource('equipment-types')
export const adminEquipment = resource('equipment')
export const adminExperimentRequirements = resource('experiment-requirements')
export const adminOrders = resource('orders')
export const adminOrderStages = resource('order-stages')
export const adminBookings = resource('bookings')

/** Aggregated dashboard statistics. */
export const fetchAdminDashboard = () => client.get('/monitoring/dashboard/')

/** Paginated, filterable activity log feed. */
export const fetchActivityLogs = (params = {}) =>
  client.get('/monitoring/logs/', { params })
