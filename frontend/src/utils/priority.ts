export const priorityOptions = [
  { value: 'P1', label: 'Low (P1)' },
  { value: 'P2', label: 'Medium (P2)' },
  { value: 'P3', label: 'High (P3)' },
  { value: 'P4', label: 'Critical (P4)' },
] as const

export function priorityLabel(value?: string | null) {
  return priorityOptions.find(option => option.value === value)?.label ?? value ?? '—'
}
