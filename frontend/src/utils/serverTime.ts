const STORAGE_KEY = 'supporthub.server-timezone'
function storedTimezone(): string | null {
  try {
    return typeof globalThis.localStorage?.getItem === 'function'
      ? globalThis.localStorage.getItem(STORAGE_KEY)
      : null
  } catch {
    return null
  }
}
let serverTimezone = storedTimezone() || 'Africa/Cairo'

const nativeDateTime = Date.prototype.toLocaleString
const nativeDate = Date.prototype.toLocaleDateString
const nativeTime = Date.prototype.toLocaleTimeString

function optionsWithServerTimezone(options?: Intl.DateTimeFormatOptions): Intl.DateTimeFormatOptions {
  return options?.timeZone ? options : { ...options, timeZone: serverTimezone }
}

// Existing screens all use the platform locale methods. Installing this once
// guarantees they share the Site Setting instead of each browser's timezone.
Date.prototype.toLocaleString = function (locales?: Intl.LocalesArgument, options?: Intl.DateTimeFormatOptions) {
  return nativeDateTime.call(this, locales, optionsWithServerTimezone(options))
}
Date.prototype.toLocaleDateString = function (locales?: Intl.LocalesArgument, options?: Intl.DateTimeFormatOptions) {
  return nativeDate.call(this, locales, optionsWithServerTimezone(options))
}
Date.prototype.toLocaleTimeString = function (locales?: Intl.LocalesArgument, options?: Intl.DateTimeFormatOptions) {
  return nativeTime.call(this, locales, optionsWithServerTimezone(options))
}

export function setServerTimezone(value: string) {
  serverTimezone = value || 'Africa/Cairo'
  try {
    if (typeof globalThis.localStorage?.setItem === 'function') {
      globalThis.localStorage.setItem(STORAGE_KEY, serverTimezone)
    }
  } catch {
    // Private browsing and constrained webviews may deny persistent storage.
  }
}

export function serverDateInput(value = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: serverTimezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(value)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

export function serverDateTimeInput(value: Date | string = new Date()): string {
  const date = typeof value === 'string' ? new Date(value) : value
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: serverTimezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`
}
