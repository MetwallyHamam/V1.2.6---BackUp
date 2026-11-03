import { describe, expect, it } from 'vitest'
import { selectedDates } from '../pages/ShiftMastersPanel'

describe('shift template date selection', () => {
  it('keeps the existing Sunday-anchored monthly pattern', () => {
    expect(selectedDates('MONTHLY_PATTERN', '2026-09', [1, 2, 3, 4], [6], 6, [], '', '')).toEqual([
      '2026-09-06',
      '2026-09-13',
      '2026-09-20',
      '2026-09-27',
    ])
  })

  it('sorts and deduplicates specific dates', () => {
    expect(selectedDates('SPECIFIC_DATES', '', [], [], 6, ['2026-09-05', '2026-09-02', '2026-09-05'], '', '')).toEqual([
      '2026-09-02',
      '2026-09-05',
    ])
  })

  it('filters an inclusive date range by weekday', () => {
    expect(selectedDates('DATE_RANGE', '', [], [0, 2], 6, [], '2026-09-07', '2026-09-13')).toEqual([
      '2026-09-07',
      '2026-09-09',
    ])
  })
})
