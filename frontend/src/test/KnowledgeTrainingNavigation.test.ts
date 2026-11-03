import { describe, expect, it } from 'vitest'
import { resolveKnowledgeSection, trainingMaterialsEndpoint } from '../pages/KnowledgePage'

describe('unified Knowledge training navigation', () => {
  it('opens the training tab only when the user can view training materials', () => {
    expect(resolveKnowledgeSection('training', true)).toBe('training')
    expect(resolveKnowledgeSection('training', false)).toBe('articles')
    expect(resolveKnowledgeSection('downloads', false)).toBe('downloads')
    expect(resolveKnowledgeSection(null, true)).toBe('articles')
  })

  it('uses the governed portal feed for client users and the employee catalog internally', () => {
    expect(trainingMaterialsEndpoint(true)).toBe('/portal/training-materials')
    expect(trainingMaterialsEndpoint(false)).toBe('/onboarding/materials')
  })
})
