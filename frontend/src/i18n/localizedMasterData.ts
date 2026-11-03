import type { SupportedLanguage } from './config'

export function getLocalizedField(
  item: object | null | undefined,
  field: string,
  language: SupportedLanguage | string,
): string {
  if (!item) return ''
  const values = item as Record<string, unknown>
  const english = values[field]
  const arabic = values[`${field}_ar`]
  if (language === 'ar' && typeof arabic === 'string' && arabic.trim()) return arabic
  return typeof english === 'string' ? english : ''
}

export function getLocalizedName(item: object | null | undefined, language: SupportedLanguage | string): string {
  return getLocalizedField(item, 'name', language)
}
