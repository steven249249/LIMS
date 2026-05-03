/**
 * Vitest setup — runs before every test file.
 *
 * Node 25 ships an experimental `globalThis.localStorage` whose object is
 * defined but whose Web Storage methods (getItem/setItem/removeItem/clear)
 * are missing. jsdom 29 surfaces the same broken object via `window.localStorage`,
 * so any production code that calls `localStorage.getItem(...)` blows up
 * with "is not a function".
 *
 * We replace it with an in-memory polyfill before any user code runs.
 */
import { afterEach, beforeEach, vi } from 'vitest'

class MemoryStorage {
  constructor() {
    this._store = new Map()
  }
  get length() { return this._store.size }
  key(i) { return Array.from(this._store.keys())[i] ?? null }
  getItem(k) { return this._store.has(k) ? this._store.get(k) : null }
  setItem(k, v) { this._store.set(String(k), String(v)) }
  removeItem(k) { this._store.delete(k) }
  clear() { this._store.clear() }
}

const memoryStorage = new MemoryStorage()
Object.defineProperty(globalThis, 'localStorage', {
  value: memoryStorage,
  configurable: true,
  writable: true,
})
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    value: memoryStorage,
    configurable: true,
    writable: true,
  })
}

beforeEach(() => {
  globalThis.localStorage.clear()
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'undefined') {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })
  }
})

afterEach(() => {
  vi.restoreAllMocks()
})
