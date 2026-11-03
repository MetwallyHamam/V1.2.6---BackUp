import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { vi } from 'vitest'

import { ClientHoursWidget } from '../components/ClientHoursWidget'

vi.mock('../api/client', () => ({
  api: {
    get: vi.fn().mockResolvedValue({
      data: {
        date_from: '2026-09-01',
        date_to: '2026-09-20',
        clients: [1, 2, 3, 4, 5].map(id => ({
          client_id: id,
          client_name: `Client ${id}`,
          working_hours: 10 - id,
          target_hours: 10,
          saved_hours: id,
        })),
      },
    }),
  },
}))

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

test('shows three clients per page and lets users reach the remaining clients', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><MemoryRouter><ClientHoursWidget dateFrom="2026-09-01" dateTo="2026-09-20" /><LocationProbe /></MemoryRouter></QueryClientProvider>)

  expect(await screen.findByRole('button', { name: /Client 1/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Client 3/ })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Client 4/ })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Go to page 2' }))
  expect(screen.getByRole('button', { name: /Client 4/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Client 5/ })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Client 1/ })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: /Client 4/ }))
  expect(screen.getByTestId('location')).toHaveTextContent('/clients/4/profile?date_from=2026-09-01&date_to=2026-09-20')
})
