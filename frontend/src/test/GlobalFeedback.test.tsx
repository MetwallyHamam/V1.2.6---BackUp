import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GlobalFeedback } from '../components/GlobalFeedback'

describe('GlobalFeedback', () => {
  it('shows backend API messages', async () => {
    render(<GlobalFeedback><div>Application</div></GlobalFeedback>)

    act(() => {
      window.dispatchEvent(new CustomEvent('support-hub-api-error', { detail: { message: 'Visit period must be within contract dates.' } }))
    })

    expect(await screen.findByText('Visit period must be within contract dates.')).toBeInTheDocument()
  })

  it('identifies required fields that fail native validation', async () => {
    render(<GlobalFeedback><label>Client<input name="client_id" required /></label></GlobalFeedback>)

    fireEvent.invalid(screen.getByRole('textbox'))

    expect(await screen.findByText('Complete the required field: client id.')).toBeInTheDocument()
  })

  it('explains that transient connection failures preserve the session',async()=>{
    render(<GlobalFeedback><div>Application</div></GlobalFeedback>)
    act(()=>window.dispatchEvent(new CustomEvent('support-hub-session-unavailable')))
    expect(await screen.findByText(/session was not signed out/i)).toBeInTheDocument()
  })
})
