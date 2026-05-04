/**
 * src/stores/settings.js — UI preferences shared across the app.
 *
 * Persists language and theme choices to localStorage and exposes them as
 * computed values for App.vue's <a-config-provider>.
 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export const SUPPORTED_LOCALES = ['zh-TW', 'en']
export const SUPPORTED_THEMES = ['light', 'dark']

const LOCALE_KEY = 'lims_locale'
const THEME_KEY = 'lims_theme'

function readPersisted(key, fallback, allowed) {
  try {
    const value = localStorage.getItem(key)
    if (value && allowed.includes(value)) return value
  } catch {
    /* SSR/incognito edge */
  }
  return fallback
}

export const useSettingsStore = defineStore('settings', () => {
  const locale = ref(readPersisted(LOCALE_KEY, 'zh-TW', SUPPORTED_LOCALES))
  const theme = ref(readPersisted(THEME_KEY, 'light', SUPPORTED_THEMES))

  watch(locale, (v) => {
    try { localStorage.setItem(LOCALE_KEY, v) } catch { /* noop */ }
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('lang', v)
    }
  })

  watch(theme, (v) => {
    try { localStorage.setItem(THEME_KEY, v) } catch { /* noop */ }
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', v)
    }
  }, { immediate: true })

  const isDark = computed(() => theme.value === 'dark')
  const isEnglish = computed(() => locale.value === 'en')

  function setLocale(v) {
    if (SUPPORTED_LOCALES.includes(v)) locale.value = v
  }
  function setTheme(v) {
    if (SUPPORTED_THEMES.includes(v)) theme.value = v
  }
  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }
  function toggleLocale() {
    setLocale(isEnglish.value ? 'zh-TW' : 'en')
  }

  return {
    locale, theme,
    isDark, isEnglish,
    setLocale, setTheme, toggleTheme, toggleLocale,
  }
})
