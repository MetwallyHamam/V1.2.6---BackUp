import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import '../i18n/config'
import { ManagerOverview } from '../pages/ManagerOverview'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { default_dashboard_scope: 'GENERAL' } }) }))
vi.mock('../api/client', () => ({ api: { get: vi.fn().mockResolvedValue({ data: { contracts_by_status: {}, contracts_expiring: {}, contracts_without_renewal_date: 3, recently_expired_contracts: 0, engineer_counts: {}, engineers_by_level: {}, engineers_by_department: {} } }) } }))

test('manager contract drill-down navigates in the current application session', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const openSpy = vi.spyOn(window, 'open')
  render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={['/']}><Routes><Route path="/" element={<ManagerOverview data={{ contracts_by_status: {}, contracts_expiring: {}, contracts_without_renewal_date: 3, recently_expired_contracts: 0, engineer_counts: {}, engineers_by_level: {}, engineers_by_department: {} }} />} /><Route path="/contracts" element={<div>Contract results</div>} /></Routes></MemoryRouter></QueryClientProvider>)
  fireEvent.click(await screen.findByText('No renewal date'))
  expect(await screen.findByText('Contract results')).toBeInTheDocument()
  expect(openSpy).not.toHaveBeenCalled()
  openSpy.mockRestore()
})
