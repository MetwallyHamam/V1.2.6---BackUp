import { act, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../components/AccessRequired', () => ({
  AccessRequired: ({ capability, compact, openSignal }: { capability:{capability:string};compact?:boolean;openSignal?:number }) => <button data-compact={String(compact)} data-open={String(openSignal??0)}>Access required: {capability.capability}</button>,
}))

import { GlobalFeedback } from '../components/GlobalFeedback'

describe('missing permission indicator', () => {
  it('shows a clickable indicator without automatically opening its dialog', async () => {
    render(<GlobalFeedback><div>Application</div></GlobalFeedback>)
    act(()=>window.dispatchEvent(new CustomEvent('support-hub-access-required',{detail:{permission:'client.view'}})))
    const indicator=await screen.findByRole('button',{name:/access required: view clients/i})
    expect(indicator).toHaveAttribute('data-compact','true')
    expect(indicator).toHaveAttribute('data-open','0')
  })
})
