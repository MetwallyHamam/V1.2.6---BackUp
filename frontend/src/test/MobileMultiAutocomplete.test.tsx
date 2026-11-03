import { fireEvent, render, screen } from '@testing-library/react'
import { createTheme, TextField, ThemeProvider } from '@mui/material'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MobileMultiAutocomplete } from '../components/MobileMultiAutocomplete'

function Fixture() {
  const [value, setValue] = useState<string[]>(['Alpha'])
  return <ThemeProvider theme={createTheme()}>
    <MobileMultiAutocomplete options={['Alpha', 'Beta']} value={value} onChange={(_, next) => setValue(next)} renderInput={params => <TextField {...params} label="Teams" />} />
    <output data-testid="committed-value">{value.join(',')}</output>
  </ThemeProvider>
}

describe('MobileMultiAutocomplete', () => {
  beforeEach(() => {
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query.includes('max-width'), media: query, onchange: null,
      addEventListener: vi.fn(), removeEventListener: vi.fn(), addListener: vi.fn(), removeListener: vi.fn(), dispatchEvent: vi.fn(),
    }))
  })

  it('keeps mobile choices as a draft until Done commits them', () => {
    render(<Fixture />)
    fireEvent.click(screen.getByLabelText('Open'))
    fireEvent.click(screen.getByRole('option', { name: 'Beta' }))
    expect(screen.getByTestId('committed-value')).toHaveTextContent('Alpha')
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(screen.getByTestId('committed-value')).toHaveTextContent('Alpha,Beta')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('restores the opening value when Cancel dismisses the menu', () => {
    render(<Fixture />)
    fireEvent.click(screen.getByLabelText('Open'))
    fireEvent.click(screen.getByRole('option', { name: 'Beta' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByTestId('committed-value')).toHaveTextContent('Alpha')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
