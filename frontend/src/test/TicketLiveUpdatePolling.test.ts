import { describe, expect, it } from 'vitest'
import { liveUpdatePollInterval, liveUpdateTimelineOrientation } from '../pages/TicketLiveUpdatePage'

describe('ticket live-update polling policy', () => {
  it('uses the active cadence until the API reports CLOSED', () => {
    expect(liveUpdatePollInterval()).toBe(30_000)
    expect(liveUpdatePollInterval({ status_code: 'RESOLVED', closed_poll_seconds: 300 })).toBe(30_000)
  })

  it('uses the configured low-frequency cadence while closed', () => {
    expect(liveUpdatePollInterval({ status_code: 'CLOSED', closed_poll_seconds: 300 })).toBe(300_000)
    expect(liveUpdatePollInterval({ status_code: 'CLOSED', closed_poll_seconds: 10 })).toBe(60_000)
  })

  it('switches the public status flow to vertical on narrow viewports', () => {
    expect(liveUpdateTimelineOrientation(true)).toBe('vertical')
    expect(liveUpdateTimelineOrientation(false)).toBe('horizontal')
  })
})
