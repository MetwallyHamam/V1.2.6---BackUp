import { afterEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import { announceSessionRestoredIfNeeded, authoritativeSessionEndReason } from '../api/client'

describe('session refresh notifications', () => {
  afterEach(() => vi.restoreAllMocks())

  it('keeps an ordinary successful token renewal silent', () => {
    const dispatch = vi.spyOn(window, 'dispatchEvent')
    expect(announceSessionRestoredIfNeeded(false)).toBe(false)
    expect(dispatch).not.toHaveBeenCalled()
  })

  it('announces recovery after a transient refresh failure', () => {
    const dispatch = vi.spyOn(window, 'dispatchEvent')
    expect(announceSessionRestoredIfNeeded(true)).toBe(true)
    expect(dispatch).toHaveBeenCalledOnce()
    expect((dispatch.mock.calls[0][0] as Event).type).toBe('support-hub-session-restored')
  })

  it('preserves the session for an unclassified 401 response', () => {
    const error = new axios.AxiosError(
      'Temporary authentication gateway response',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      {
        data: '<html>temporarily unavailable</html>',
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config: { headers: new axios.AxiosHeaders() },
      },
    )
    expect(authoritativeSessionEndReason(error)).toBeNull()
  })

  it('ends the session only for a definitive refresh-token rejection', () => {
    const error = new axios.AxiosError(
      'Expired refresh token',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      {
        data: { error: { code: 'REFRESH_TOKEN_EXPIRED' } },
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config: { headers: new axios.AxiosHeaders() },
      },
    )
    expect(authoritativeSessionEndReason(error)).toBe('expired')
  })
})
