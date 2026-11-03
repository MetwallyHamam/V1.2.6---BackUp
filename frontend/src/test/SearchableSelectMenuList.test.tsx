import { FormControl, InputLabel, MenuItem, Select } from '@mui/material'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SearchableSelectMenuList } from '../components/SearchableSelectMenuList'

function renderSelect() {
  render(
    <FormControl>
      <InputLabel id="client-label">Client</InputLabel>
      <Select
        labelId="client-label"
        label="Client"
        value=""
        MenuProps={{
          slots: { list: SearchableSelectMenuList },
          disableEnforceFocus: true,
          disableAutoFocusItem: true,
          anchorOrigin: { vertical: 'bottom', horizontal: 'left' },
          transformOrigin: { vertical: 'top', horizontal: 'left' },
        }}
      >
        <MenuItem value="cairo">Cairo Scan</MenuItem>
        <MenuItem value="alex">Alexandria Medical</MenuItem>
        <MenuItem value="accent">Clinique Égypte</MenuItem>
      </Select>
    </FormControl>,
  )
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Client' }))
}

describe('SearchableSelectMenuList', () => {
  afterEach(cleanup)

  it('integrates search into a real Select and filters by case-insensitive contained text', async () => {
    renderSelect()

    const search = screen.getByLabelText('Search dropdown options')
    expect(search.closest('[role="listbox"]')).toBeNull()
    await waitFor(() => expect(search).toHaveFocus())
    expect(screen.getByRole('listbox').querySelector('input')).toBeNull()
    await waitFor(() => expect(screen.getByRole('listbox').parentElement?.style.getPropertyValue('top')).toBe('6px'))
    fireEvent.change(search, { target: { value: 'SCAN' } })

    expect(screen.getByRole('option', { name: 'Cairo Scan' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Alexandria Medical' })).not.toBeInTheDocument()
  })

  it('normalizes accents and shows an empty result without closing the dropdown', () => {
    renderSelect()
    const search = screen.getByLabelText('Search dropdown options')

    fireEvent.change(search, { target: { value: 'egypte' } })
    expect(screen.getByRole('option', { name: 'Clinique Égypte' })).toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'missing' } })
    expect(screen.getByRole('status')).toHaveTextContent('No matching options')
    expect(screen.getByRole('listbox')).toBeInTheDocument()
  })

  it('accepts typing in the select field immediately without a second click', async () => {
    renderSelect()
    const field = await screen.findByRole('searchbox', { name: 'Search dropdown options' })
    await waitFor(() => expect(field).toHaveFocus())

    fireEvent.change(field, { target: { value: 'andria' } })

    expect(field).toHaveValue('andria')
    expect(screen.getByRole('option', { name: 'Alexandria Medical' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Cairo Scan' })).not.toBeInTheDocument()
  })
})
