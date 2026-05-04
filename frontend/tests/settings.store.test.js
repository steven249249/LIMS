// @vitest-environment jsdom
/**
 * Unit tests for the settings Pinia store.
 *
 * Verifies locale + theme defaults, persistence, and the convenience toggles.
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useSettingsStore } from '../src/stores/settings'

describe('settings store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('defaults to zh-TW locale and light theme on first run', () => {
    const settings = useSettingsStore()
    expect(settings.locale).toBe('zh-TW')
    expect(settings.theme).toBe('light')
    expect(settings.isDark).toBe(false)
    expect(settings.isEnglish).toBe(false)
  })

  it('reads previously persisted locale from localStorage', () => {
    localStorage.setItem('lims_locale', 'en')
    const settings = useSettingsStore()
    expect(settings.locale).toBe('en')
    expect(settings.isEnglish).toBe(true)
  })

  it('reads previously persisted theme from localStorage', () => {
    localStorage.setItem('lims_theme', 'dark')
    const settings = useSettingsStore()
    expect(settings.theme).toBe('dark')
    expect(settings.isDark).toBe(true)
  })

  it('ignores unknown persisted values and falls back to defaults', () => {
    localStorage.setItem('lims_locale', 'klingon')
    localStorage.setItem('lims_theme', 'sunset')
    const settings = useSettingsStore()
    expect(settings.locale).toBe('zh-TW')
    expect(settings.theme).toBe('light')
  })

  it('setLocale persists the new value', async () => {
    const settings = useSettingsStore()
    settings.setLocale('en')
    // wait a microtask for the watcher to flush
    await Promise.resolve()
    expect(settings.locale).toBe('en')
    expect(localStorage.getItem('lims_locale')).toBe('en')
  })

  it('setLocale rejects unknown values', () => {
    const settings = useSettingsStore()
    settings.setLocale('jp')
    expect(settings.locale).toBe('zh-TW')
  })

  it('toggleTheme flips between light and dark', async () => {
    const settings = useSettingsStore()
    settings.toggleTheme()
    await Promise.resolve()
    expect(settings.theme).toBe('dark')
    settings.toggleTheme()
    await Promise.resolve()
    expect(settings.theme).toBe('light')
  })

  it('toggleLocale flips between zh-TW and en', async () => {
    const settings = useSettingsStore()
    settings.toggleLocale()
    await Promise.resolve()
    expect(settings.locale).toBe('en')
    settings.toggleLocale()
    await Promise.resolve()
    expect(settings.locale).toBe('zh-TW')
  })

  it('writes data-theme on documentElement when theme changes', async () => {
    const settings = useSettingsStore()
    settings.setTheme('dark')
    await Promise.resolve()
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
})
