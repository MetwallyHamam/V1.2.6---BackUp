import { act, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

const authState = vi.hoisted(() => ({
  user: null as null | { preferred_language: 'en' | 'ar' },
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: authState.user }),
}))

import i18n, { LANGUAGE_STORAGE_KEY } from '../i18n/config'
import { LanguageProvider } from '../i18n/LanguageProvider'

const storageValues = new Map<string, string>()

beforeEach(async () => {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      clear: () => storageValues.clear(),
      getItem: (key: string) => storageValues.get(key) ?? null,
      key: (index: number) => [...storageValues.keys()][index] ?? null,
      get length() { return storageValues.size },
      removeItem: (key: string) => storageValues.delete(key),
      setItem: (key: string, value: string) => storageValues.set(key, String(value)),
    },
  })
  authState.user = null
  window.localStorage.clear()
  await act(async () => { await i18n.changeLanguage('en') })
})

afterEach(async () => {
  authState.user = null
  window.localStorage.clear()
  await act(async () => { await i18n.changeLanguage('en') })
  document.documentElement.lang = 'en'
  document.documentElement.dir = 'ltr'
})

describe('language preference persistence', () => {
  test('restores a cached language when the application module reloads', async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'ar')
    vi.resetModules()

    const fresh = await import('../i18n/config')

    expect(fresh.default.language).toBe('ar')
    expect(fresh.default.dir()).toBe('rtl')
  })

  test('reapplies the authenticated preference after re-login and persists direction', async () => {
    authState.user = { preferred_language: 'ar' }
    const view = render(<LanguageProvider><div>Application</div></LanguageProvider>)

    await waitFor(() => {
      expect(i18n.language).toBe('ar')
      expect(document.documentElement.lang).toBe('ar')
      expect(document.documentElement.dir).toBe('rtl')
      expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('ar')
    })

    authState.user = null
    view.rerender(<LanguageProvider><div>Application</div></LanguageProvider>)
    authState.user = { preferred_language: 'ar' }
    view.rerender(<LanguageProvider><div>Application</div></LanguageProvider>)

    await waitFor(() => {
      expect(i18n.language).toBe('ar')
      expect(document.documentElement.dir).toBe('rtl')
      expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('ar')
    })
  })
})
