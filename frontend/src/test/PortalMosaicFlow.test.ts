import { describe, expect, it } from 'vitest'
import { isMosaicMode, servicesForModule } from '../pages/PortalCreateTicketPage'

describe('B-44 guided Mosaic flow', () => {
  it('keeps Mosaic explicit and does not switch the normal portal path', () => {
    expect(isMosaicMode('mosaic')).toBe(true)
    expect(isMosaicMode('MOSAIC')).toBe(true)
    expect(isMosaicMode(null)).toBe(false)
    expect(isMosaicMode('portal')).toBe(false)
  })

  it('shows only services linked to the selected module', () => {
    const services = [
      { id: 1, name: 'Workspace VNA', covered: true, module_ids: [10, 11] },
      { id: 2, name: 'Viewer', covered: false, module_ids: [11] },
      { id: 3, name: 'Unlinked', covered: true, module_ids: [] },
    ]
    expect(servicesForModule(services, '10').map(item => item.id)).toEqual([1])
    expect(servicesForModule(services, '11').map(item => item.id)).toEqual([1, 2])
    expect(servicesForModule(services, '')).toEqual([])
  })
})
