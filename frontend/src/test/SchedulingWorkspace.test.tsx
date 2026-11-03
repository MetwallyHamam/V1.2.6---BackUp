import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import '../i18n/config'

const auth=vi.hoisted(()=>({permissions:new Set<string>()}))
vi.mock('../auth/AuthContext',()=>({useAuth:()=>({hasPermission:(permission:string)=>auth.permissions.has(permission)})}))
vi.mock('../pages/SchedulingOverviewPage',()=>({SchedulingOverviewPage:()=> <div>Overview dashboard content</div>}))
vi.mock('../pages/SchedulingWorkloadPage',()=>({SchedulingWorkloadPage:()=> <div>Workload content</div>}))
vi.mock('../pages/SchedulingSetupPage',()=>({SchedulingSetupPage:()=> <div>Setup content</div>}))
vi.mock('../pages/ShiftsPage',()=>({ShiftsPage:()=> <div>Unified calendar content</div>}))
vi.mock('../pages/InternalOperationsPage',()=>({InternalOperationsPage:()=> <div>Internal operation content</div>}))
vi.mock('../pages/VisitOperationsPage',()=>({VisitOperationsPage:()=> <div>Field visit content</div>}))
vi.mock('../pages/OperationalReportsPage',()=>({OperationalReportsPage:()=> <div>Legacy reports content</div>}))

import { OperationsWorkspacePage } from '../pages/OperationsWorkspacePage'

beforeEach(()=>{auth.permissions=new Set(['shift.view','shift.manage','shift.create','internal_operation.view','internal_operation.manage','visit.entitlement.view'])})

test('exposes the four scheduling areas and switches planner sources',()=>{
  render(<MemoryRouter initialEntries={['/internal-operations']}><OperationsWorkspacePage/></MemoryRouter>)
  expect(screen.getByText('Overview dashboard content')).toBeInTheDocument()
  for(const label of ['Overview','Planner','Workload','Setup'])expect(screen.getByRole('tab',{name:label})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab',{name:'Planner'}))
  expect(screen.getByText('Unified calendar content')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab',{name:'Internal operations'}))
  expect(screen.getByText('Internal operation content')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab',{name:'Workload'}))
  expect(screen.getByText('Workload content')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab',{name:'Setup'}))
  expect(screen.getByText('Setup content')).toBeInTheDocument()
  expect(screen.getByLabelText('Quick scheduling actions')).toBeInTheDocument()
})

test('hides management-only workload and setup tabs without shift access',()=>{
  auth.permissions=new Set(['internal_operation.view'])
  render(<MemoryRouter initialEntries={['/internal-operations']}><OperationsWorkspacePage/></MemoryRouter>)
  expect(screen.queryByRole('tab',{name:'Workload'})).not.toBeInTheDocument()
  expect(screen.queryByRole('tab',{name:'Setup'})).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab',{name:'Planner'}))
  expect(screen.getByText('Internal operation content')).toBeInTheDocument()
})
