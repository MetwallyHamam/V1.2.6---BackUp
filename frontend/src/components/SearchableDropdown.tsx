import { Autocomplete, SxProps, TextField, Theme, createFilterOptions } from '@mui/material'

export type SearchableDropdownOption = { value: string | number; label: string }

const containsFilter = createFilterOptions<SearchableDropdownOption>({
  ignoreAccents: true,
  ignoreCase: true,
  matchFrom: 'any',
  stringify: option => option.label,
  trim: true,
})

export function SearchableDropdown({ label, value, options, onChange, disabled, required, size, margin, sx }: {
  label: string
  value: string
  options: SearchableDropdownOption[]
  onChange: (value: string) => void
  disabled?: boolean
  required?: boolean
  size?: 'small' | 'medium'
  margin?: 'none' | 'dense' | 'normal'
  sx?: SxProps<Theme>
}) {
  const selected = value ? options.find(option => String(option.value) === value) ?? null : null
  return <Autocomplete
    autoHighlight
    openOnFocus
    selectOnFocus
    clearOnBlur
    handleHomeEndKeys
    disabled={disabled}
    options={options}
    value={selected}
    filterOptions={containsFilter}
    isOptionEqualToValue={(option, candidate) => String(option.value) === String(candidate.value)}
    getOptionLabel={option => option.label}
    onChange={(_, option) => onChange(option ? String(option.value) : '')}
    noOptionsText="No matching options"
    sx={sx}
    slotProps={{ popper: { placement: 'bottom-start', modifiers: [{ name: 'offset', options: { offset: [0, 8] } }] } }}
    renderInput={params => <TextField {...params} label={label} required={required} size={size} margin={margin} />}
  />
}
