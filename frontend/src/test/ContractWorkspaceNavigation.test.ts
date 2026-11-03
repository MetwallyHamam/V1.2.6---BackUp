import { describe, expect, it } from 'vitest'
import { resolveContractWorkspaceSection } from '../pages/ContractWorkspacePage'

describe('contract workspace navigation', () => {
  it('opens the requested section when the user can view it', () => {
    expect(resolveContractWorkspaceSection('contracts', true, true)).toBe('contracts')
    expect(resolveContractWorkspaceSection('templates', true, true)).toBe('templates')
    expect(resolveContractWorkspaceSection('sla-templates', true, true)).toBe('sla-templates')
    expect(resolveContractWorkspaceSection('notifications', true, true, true)).toBe('notifications')
  })

  it('falls back to the section allowed by the effective permissions', () => {
    expect(resolveContractWorkspaceSection('templates', true, false)).toBe('lifecycle')
    expect(resolveContractWorkspaceSection('sla-templates', false, true)).toBe('templates')
    expect(resolveContractWorkspaceSection(null, false, true)).toBe('templates')
    expect(resolveContractWorkspaceSection('notifications', true, true, false)).toBe('lifecycle')
  })
})
