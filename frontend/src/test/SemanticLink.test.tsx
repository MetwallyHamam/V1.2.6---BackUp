import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { SemanticLink } from '../components/SemanticLink'

describe('SemanticLink', () => {
  it('renders a browser-native anchor with a stable href', () => {
    render(<MemoryRouter><SemanticLink to="/tickets/42">Open ticket 42</SemanticLink></MemoryRouter>)
    const link = screen.getByRole('link', { name: 'Open ticket 42' })
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', '/tickets/42')
  })
})
