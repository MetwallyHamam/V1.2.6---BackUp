import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import i18n from '../i18n/config'

const apiMock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../api/client', () => ({ api: apiMock }))

import { PortalTicketsPage } from '../pages/PortalTicketsPage'
import { QuickShiftDialog } from '../pages/QuickShiftDialog'

function queryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
}

beforeEach(async () => {
  apiMock.get.mockReset()
  apiMock.post.mockReset()
  await i18n.changeLanguage('ar')
  document.documentElement.lang = 'ar'
  document.documentElement.dir = 'rtl'
})

afterEach(async () => {
  await i18n.changeLanguage('en')
  document.documentElement.lang = 'en'
  document.documentElement.dir = 'ltr'
})

describe('representative RTL pages', () => {
  test('portal ticket list renders Arabic master data and isolates request numbers', async () => {
    apiMock.get.mockImplementation((url: string) => Promise.resolve({ data:
      url === '/portal/tickets' ? [{ id: 8, ticket_number: 'TKT-2026-0008', subject: 'تعطل الخدمة', priority: 'P2', status_id: 3, product_id: 4, service_id: 5, created_at: '2026-08-30T08:00:00Z', updated_at: '2026-08-30T09:00:00Z' }]
      : url === '/ticket-statuses' ? [{ id: 3, name: 'In progress', name_ar: 'قيد التنفيذ', color: '#1565c0' }]
      : { products: [{ id: 4, name: 'Archive', name_ar: 'الأرشيف' }], modules: [], services: [{ id: 5, name: 'Viewer', name_ar: 'العارض' }] }
    }))

    render(<MemoryRouter><QueryClientProvider client={queryClient()}><PortalTicketsPage /></QueryClientProvider></MemoryRouter>)

    expect(await screen.findByText('الأرشيف')).toBeInTheDocument()
    expect(screen.getByText('قيد التنفيذ')).toBeInTheDocument()
    const requestLinks = screen.getByLabelText('Request links')
    expect(requestLinks.querySelector('[data-technical-text="true"]')).toHaveTextContent('TKT-2026-0008')
    expect(document.documentElement.dir).toBe('rtl')
  })

  test('internal quick-shift dialog renders the Arabic shift type', async () => {
    apiMock.get.mockResolvedValue({ data: [{ id: 7, name: 'Morning', name_ar: 'الفترة الصباحية', color: '#145da0', default_start_time: '09:00:00', default_end_time: '17:00:00', default_required_headcount: 2, crosses_midnight: false }] })

    render(<QueryClientProvider client={queryClient()}><QuickShiftDialog open initialDate="2026-08-31" onClose={vi.fn()} /></QueryClientProvider>)

    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith('/shift-types'))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /نوع|Shift Type/i }))
    expect(await screen.findByText('الفترة الصباحية')).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
  })
})
