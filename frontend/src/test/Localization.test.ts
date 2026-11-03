import { afterEach, describe, expect, test } from 'vitest'

import i18n from '../i18n/config'
import { getLocalizedField, getLocalizedName } from '../i18n/localizedMasterData'

afterEach(async () => {
  await i18n.changeLanguage('en')
})

describe('localization foundation', () => {
  test('English is the source language and Arabic labels are available', async () => {
    await i18n.changeLanguage('en')
    expect(i18n.t('common.actions.save')).toBe('Save')

    await i18n.changeLanguage('ar')
    expect(i18n.t('common.actions.save')).toBe('حفظ')
    expect(i18n.dir()).toBe('rtl')
  })

  test('missing Arabic keys fall back to English', async () => {
    i18n.addResource('en', 'translation', 'test.englishOnly', 'English fallback')
    await i18n.changeLanguage('ar')
    expect(i18n.t('test.englishOnly')).toBe('English fallback')
  })

  test('database master data uses Arabic with a safe English fallback', () => {
    expect(getLocalizedName({ name: 'Support', name_ar: 'الدعم' }, 'ar')).toBe('الدعم')
    expect(getLocalizedName({ name: 'Legacy value', name_ar: null }, 'ar')).toBe('Legacy value')
    expect(getLocalizedField({ description: 'English', description_ar: 'العربية' }, 'description', 'ar')).toBe('العربية')
  })
})
