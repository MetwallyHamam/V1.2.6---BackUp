import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

const auth = vi.hoisted(() => ({ permissions: new Set<string>() }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ hasPermission: (permission: string) => auth.permissions.has(permission) }) }))

import { PermissionRoute } from '../routes/PermissionRoute'

beforeEach(() => { auth.permissions = new Set() })

test('project delivery permissions do not open contract or operations workspaces', () => {
  auth.permissions = new Set(['project_handover.view', 'project_handover.manage', 'project_handover.contract_template.apply', 'project_handover.engineer.lookup'])
  render(<MemoryRouter initialEntries={['/contracts']}><Routes>
    <Route element={<PermissionRoute anyOf={['contract.view', 'contract.template.view']} />}><Route path="/contracts" element={<div>Contract workspace</div>} /></Route>
    <Route path="/unauthorized" element={<div>Access denied</div>} />
  </Routes></MemoryRouter>)
  expect(screen.getByText('Access denied')).toBeInTheDocument()
  expect(screen.queryByText('Contract workspace')).not.toBeInTheDocument()
})

test('an exact workspace permission opens its route', () => {
  auth.permissions = new Set(['contract.view'])
  render(<MemoryRouter initialEntries={['/contracts']}><Routes>
    <Route element={<PermissionRoute anyOf={['contract.view', 'contract.template.view']} />}><Route path="/contracts" element={<div>Contract workspace</div>} /></Route>
  </Routes></MemoryRouter>)
  expect(screen.getByText('Contract workspace')).toBeInTheDocument()
})
