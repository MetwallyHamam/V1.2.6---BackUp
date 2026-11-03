import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

const auth = vi.hoisted(() => ({ userType: 'CLIENT_PORTAL' as 'CLIENT_PORTAL' | 'EMPLOYEE' }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { user_type: auth.userType } }) }))

import { InternalUserRoute } from '../routes/InternalUserRoute'

test('redirects a client portal user away from Support Now', () => {
  auth.userType = 'CLIENT_PORTAL'
  render(<MemoryRouter initialEntries={['/home']}><Routes>
    <Route element={<InternalUserRoute />}><Route path="/home" element={<div>Support Now</div>} /></Route>
    <Route path="/portal" element={<div>Client portal</div>} />
  </Routes></MemoryRouter>)
  expect(screen.getByText('Client portal')).toBeInTheDocument()
  expect(screen.queryByText('Support Now')).not.toBeInTheDocument()
})

test('allows an employee to open Support Now', () => {
  auth.userType = 'EMPLOYEE'
  render(<MemoryRouter initialEntries={['/home']}><Routes>
    <Route element={<InternalUserRoute />}><Route path="/home" element={<div>Support Now</div>} /></Route>
  </Routes></MemoryRouter>)
  expect(screen.getByText('Support Now')).toBeInTheDocument()
})
