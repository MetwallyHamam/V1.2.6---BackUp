import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PortalUatWorkspace, type PortalWorkspaceTest } from '../pages/PortalUatWorkspace'

const test: PortalWorkspaceTest = {
  id: 7,
  snapshot: { code: 'UAT-007', title: 'Client can test the workflow', priority: 'HIGH' },
  client_test_result: 'NOT_TESTED',
  client_workflow_status: 'READY',
  client_attempt_count: 0,
  linked_ticket: null,
  assigned_to_me: true,
}

const cycle = {
  allow_client_testing: true,
  allow_client_pass: true,
  allow_client_fail: true,
  allow_client_blocked: true,
  client_signoff_current: false,
}

describe('PortalUatWorkspace', () => {
  it('opens a card and exposes status actions from the right-click menu', () => {
    const onOpen = vi.fn()
    const onMove = vi.fn()
    render(<PortalUatWorkspace cycle={cycle} tests={[test]} selectedId={null} moving={false} onMove={onMove} onOpen={onOpen} />)

    const card = screen.getByLabelText(/UAT-007 UAT test card/i)
    fireEvent.click(card)
    expect(onOpen).toHaveBeenCalledWith(test)

    fireEvent.contextMenu(card, { clientX: 20, clientY: 20 })
    fireEvent.click(screen.getByRole('menuitem', { name: 'Start testing' }))
    expect(onMove).toHaveBeenCalledWith(7, 'IN_PROGRESS')
  })

  it('moves an assigned card when it is dropped in the testing lane', () => {
    const onMove = vi.fn()
    render(<PortalUatWorkspace cycle={cycle} tests={[test]} selectedId={null} moving={false} onMove={onMove} onOpen={vi.fn()} />)

    const card = screen.getByLabelText(/UAT-007 UAT test card/i)
    const transfer = { effectAllowed: '', dropEffect: '', setData: vi.fn() }
    fireEvent.dragStart(card, { dataTransfer: transfer })
    const lane = screen.getByText('In testing').closest('.MuiPaper-root')
    expect(lane).not.toBeNull()
    fireEvent.dragOver(lane!, { dataTransfer: transfer })
    fireEvent.drop(lane!, { dataTransfer: transfer })
    expect(onMove).toHaveBeenCalledWith(7, 'IN_PROGRESS')
  })
})
