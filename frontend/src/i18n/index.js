import { createI18n } from 'vue-i18n'
import zhTW from './zh-TW'
import en from './en'

const STORAGE_KEY = 'lims_locale'

function readStoredLocale() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'zh-TW' || v === 'en') return v
  } catch {
    /* SSR / incognito */
  }
  return 'zh-TW'
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: readStoredLocale(),
  fallbackLocale: 'zh-TW',
  messages: { 'zh-TW': zhTW, en },
})

export default i18n
