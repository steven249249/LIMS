// @vitest-environment jsdom
/**
 * Component tests for CrudTable.
 *
 * Antd's table/modal/form internals are stubbed out — we only verify the
 * orchestration logic the page itself owns:
 *   - Initial load fires resource.list with the right pagination params.
 *   - Search and reload trigger reload.
 *   - Create / edit / delete invoke the right resource methods.
 *   - Write-only (password) fields are dropped from update payloads
 *     when left empty, but kept on create.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('ant-design-vue', () => ({
  message: { success: vi.fn(), error: vi.fn() },
}))

import CrudTable from '../src/components/admin/CrudTable.vue'

const STUBS = [
  'a-page-header', 'a-input-search', 'a-button', 'a-table',
  'a-modal', 'a-form', 'a-form-item', 'a-row', 'a-col',
  'a-input', 'a-textarea', 'a-input-number', 'a-input-password',
  'a-select', 'a-select-option', 'a-switch', 'a-popconfirm', 'a-space', 'a-tag',
  'PlusOutlined', 'ReloadOutlined', 'EditOutlined', 'DeleteOutlined',
]

function makeResource(overrides = {}) {
  return {
    list: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
    retrieve: vi.fn(),
    create: vi.fn().mockResolvedValue({ data: { id: 'new-1' } }),
    update: vi.fn().mockResolvedValue({ data: { id: 'u-1' } }),
    remove: vi.fn().mockResolvedValue({}),
    ...overrides,
  }
}

const defaultColumns = [
  { title: 'Name', dataIndex: 'name' },
]
const defaultFormFields = [
  { name: 'name', label: 'Name', type: 'text', required: true },
]

async function mountTable(props = {}) {
  const wrapper = mount(CrudTable, {
    props: {
      resource: makeResource(),
      resourceLabel: 'item',
      title: 'Items',
      columns: defaultColumns,
      formFields: defaultFormFields,
      ...props,
    },
    global: { stubs: STUBS },
  })
  await flushPromises()
  return wrapper
}

describe('CrudTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads data on mount with default pagination', async () => {
    // Arrange
    const resource = makeResource()
    // Act
    await mountTable({ resource })
    // Assert
    expect(resource.list).toHaveBeenCalledTimes(1)
    expect(resource.list).toHaveBeenCalledWith({
      page: 1,
      page_size: 20,
    })
  })

  it('forwards search text on search()', async () => {
    // Arrange
    const resource = makeResource()
    const wrapper = await mountTable({ resource })
    resource.list.mockClear()
    // Act
    wrapper.vm.searchText = 'sem'
    wrapper.vm.onSearch()
    await flushPromises()
    // Assert
    expect(resource.list).toHaveBeenCalledWith({
      page: 1,
      page_size: 20,
      search: 'sem',
    })
  })

  it('openCreate() initialises form with field defaults', async () => {
    // Arrange
    const formFields = [
      { name: 'name', label: 'Name', type: 'text', defaultValue: 'preset' },
      { name: 'flag', label: 'Flag', type: 'switch' },
    ]
    const wrapper = await mountTable({ formFields })
    // Act
    wrapper.vm.openCreate()
    // Assert
    expect(wrapper.vm.modalOpen).toBe(true)
    expect(wrapper.vm.editingId).toBeNull()
    expect(wrapper.vm.formState.name).toBe('preset')
    expect(wrapper.vm.formState.flag).toBe(false)
  })

  it('openEdit() seeds form from record but blanks writeOnly fields', async () => {
    // Arrange
    const formFields = [
      { name: 'username', label: 'User', type: 'text' },
      { name: 'password', label: 'Pwd', type: 'password', writeOnly: true },
    ]
    const wrapper = await mountTable({ formFields })
    const record = { id: 'r-1', username: 'alice', password: 'cant-leak' }
    // Act
    wrapper.vm.openEdit(record)
    // Assert
    expect(wrapper.vm.editingId).toBe('r-1')
    expect(wrapper.vm.formState.username).toBe('alice')
    expect(wrapper.vm.formState.password).toBe('')
  })

  it('buildPayload() drops empty writeOnly fields when editing', async () => {
    // Arrange
    const formFields = [
      { name: 'username', label: 'User', type: 'text' },
      { name: 'password', label: 'Pwd', type: 'password', writeOnly: true },
    ]
    const wrapper = await mountTable({ formFields })
    wrapper.vm.openEdit({ id: 'r-1', username: 'alice', password: 'old-hash' })
    wrapper.vm.formState.username = 'alice2'
    // password left as empty string
    // Act
    const payload = wrapper.vm.buildPayload()
    // Assert
    expect(payload).toEqual({ username: 'alice2' })
    expect(payload.password).toBeUndefined()
  })

  it('buildPayload() keeps writeOnly fields when creating', async () => {
    // Arrange
    const formFields = [
      { name: 'username', label: 'User', type: 'text' },
      { name: 'password', label: 'Pwd', type: 'password', writeOnly: true },
    ]
    const wrapper = await mountTable({ formFields })
    wrapper.vm.openCreate()
    wrapper.vm.formState.username = 'newuser'
    wrapper.vm.formState.password = 'fresh!'
    // Act
    const payload = wrapper.vm.buildPayload()
    // Assert
    expect(payload).toEqual({ username: 'newuser', password: 'fresh!' })
  })

  it('onDelete() calls resource.remove and reloads', async () => {
    // Arrange
    const resource = makeResource({
      list: vi
        .fn()
        .mockResolvedValueOnce({ data: { results: [{ id: 'x' }], count: 1 } })
        .mockResolvedValueOnce({ data: { results: [], count: 0 } }),
    })
    const wrapper = await mountTable({ resource })
    // Act
    await wrapper.vm.onDelete({ id: 'x' })
    await flushPromises()
    // Assert
    expect(resource.remove).toHaveBeenCalledWith('x')
    expect(resource.list).toHaveBeenCalledTimes(2)   // initial load + reload
  })

  it('handleApiError surfaces validation envelope', async () => {
    // Arrange
    const resource = makeResource()
    const wrapper = await mountTable({ resource })
    const { message } = await import('ant-design-vue')
    // Act
    wrapper.vm.handleApiError(
      { response: { data: { detail: 'Validation failed.' } } },
      'fallback',
    )
    // Assert
    expect(message.error).toHaveBeenCalledWith('Validation failed.')
  })
})
