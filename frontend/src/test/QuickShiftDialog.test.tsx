import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import '../i18n/config'

const apiMock=vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}))
vi.mock('../api/client',()=>({api:apiMock}))

import { QuickShiftDialog } from '../pages/QuickShiftDialog'

beforeEach(()=>{
  apiMock.get.mockReset();apiMock.post.mockReset()
  apiMock.get.mockImplementation((url:string)=>Promise.resolve({data:url==='/shift-types'?[{id:7,name:'Weekend Morning',color:'#145da0',default_start_time:'09:00:00',default_end_time:'17:00:00',default_required_headcount:2,crosses_midnight:false}]:{date:'2026-08-28',shift_type_id:7,starts_at:'2026-08-28T06:00:00Z',ends_at:'2026-08-28T14:00:00Z',timezone:'Africa/Cairo',required_headcount:2,candidates:[{employee_id:11,employee_name:'Ali Abdelaleem',eligible:true,available:true,shift_conflict:false,operation_conflict:false,visit_conflict:false,shift_count:1,shift_minutes:480,operation_minutes:0,visit_minutes:0,reason:'Eligible and available'},{employee_id:12,employee_name:'Inactive User',eligible:true,available:false,shift_conflict:true,operation_conflict:false,visit_conflict:false,shift_count:2,shift_minutes:960,operation_minutes:0,visit_minutes:0,reason:'Overlapping shift'}]}}))
  apiMock.post.mockResolvedValue({data:{created:1}})
})

test('manual shift range is Date From → Date To → Shift Type → Engineers → Create',async()=>{
  const onClose=vi.fn(),queryClient=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})
  render(<QueryClientProvider client={queryClient}><QuickShiftDialog open initialDate="2026-08-28" onClose={onClose}/></QueryClientProvider>)
  expect(screen.getByLabelText(/Date From/)).toHaveValue('2026-08-28')
  fireEvent.change(screen.getByLabelText(/Date To/),{target:{value:'2026-08-30'}})
  fireEvent.mouseDown(screen.getByRole('combobox',{name:/Shift Type/}))
  fireEvent.click(await screen.findByRole('option',{name:'Weekend Morning'}))
  expect(await screen.findByText('09:00 → 17:00')).toBeInTheDocument()
  expect(screen.getByText(/Inherited from Shift Type/)).toBeInTheDocument()
  const engineers=await screen.findByLabelText('Engineers')
  fireEvent.change(engineers,{target:{value:'Ali'}})
  fireEvent.click(await screen.findByText('Ali Abdelaleem'))
  expect(screen.getByText(/Daily coverage 1 \/ 2/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Create 3 Days'}))
  await waitFor(()=>expect(apiMock.post).toHaveBeenCalledWith('/shifts/quick',expect.objectContaining({date_from:'2026-08-28',date_to:'2026-08-30',shift_type_id:7,assignment_mode:'MANUAL',user_ids:[11]})))
  expect(onClose).toHaveBeenCalled()
})
