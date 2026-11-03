import { describe, expect, it } from 'vitest'

import { DASHBOARD_ANALYSIS_TIMEOUT_MS } from '../api/client'

describe('historical dashboard request timeout', () => {
  it('allows two minutes without weakening the normal API timeout', async () => {
    const { api } = await import('../api/client')

    expect(api.defaults.timeout).toBe(30_000)
    expect(DASHBOARD_ANALYSIS_TIMEOUT_MS).toBe(120_000)
  })
})
