import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { SearchableDropdown } from '../components/SearchableDropdown'

function PortalDropdown() {
  const [value, setValue] = useState('')
  return <SearchableDropdown
    label="Portal client"
    value={value}
    onChange={setValue}
    options={[
      { value: '', label: 'All clients' },
      { value: 1, label: 'Cairo Scan Center' },
      { value: 2, label: 'Alexandria Medical' },
    ]}
  />
}

describe('SearchableDropdown', () => {
  it('types directly in the field and filters portal options by contained text', () => {
    render(<PortalDropdown />)
    const field = screen.getByRole('combobox', { name: 'Portal client' })

    fireEvent.focus(field)
    fireEvent.change(field, { target: { value: 'scan' } })

    expect(field).toHaveValue('scan')
    expect(screen.getByRole('option', { name: 'Cairo Scan Center' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Alexandria Medical' })).not.toBeInTheDocument()
  })

  it('matches text in the middle of a portal option without case sensitivity', () => {
    render(<PortalDropdown />)
    const field = screen.getByRole('combobox', { name: 'Portal client' })

    fireEvent.focus(field)
    fireEvent.change(field, { target: { value: 'DRIA' } })

    expect(screen.getByRole('option', { name: 'Alexandria Medical' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Cairo Scan Center' })).not.toBeInTheDocument()
  })
})
