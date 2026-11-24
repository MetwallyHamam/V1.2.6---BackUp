// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { EMPTY_PORTFOLIO_FILTERS, filterPortfolio, type PortfolioRow } from '../pages/UatPortfolioPanel'

const base = {
  title: 'Cycle', environment: 'UAT', status: 'ACTIVE', coordinator_user_id: 7,
  coordinator_name: 'Coordinator', due_date: null, due_state: 'NO_DUE_DATE',
  metrics: { completion_percent: 20, pass_rate: 50, failed: 1, critical_failures: 0, open_defects: 0, blocked: 0 },
  client_total: 1, client_passed: 0, client_signoff: 'NOT_REQUESTED', internal_signoff: 'NOT_REQUESTED',
  awaiting_client: false, ready_for_signoff: false, next_action: 'Review Failures', urgency_rank: 1,
}
const rows: PortfolioRow[] = [
  { ...base, id: 1, code: 'UAT-1', client_id: 10, client_name: 'Acme', release_version: '1.0', attention: ['Failures without tickets'] },
  { ...base, id: 2, code: 'UAT-2', client_id: 20, client_name: 'Beta', release_version: '2.0', due_state: 'OVERDUE', attention: ['Overdue tests'] },
]

describe('UAT portfolio filters', () => {
  it('composes governed client, release, due and attention filters', () => {
    expect(filterPortfolio(rows, { ...EMPTY_PORTFOLIO_FILTERS, client: '10', release: '1.0' }).map((row) => row.id)).toEqual([1])
    expect(filterPortfolio(rows, { ...EMPTY_PORTFOLIO_FILTERS, due: 'OVERDUE', attention: 'Overdue tests' }).map((row) => row.id)).toEqual([2])
  })

  it('returns the complete API order when filters are clear', () => {
    expect(filterPortfolio(rows, EMPTY_PORTFOLIO_FILTERS).map((row) => row.id)).toEqual([1, 2])
  })
})
