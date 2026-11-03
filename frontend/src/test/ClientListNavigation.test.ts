import { describe, expect, it } from 'vitest'
import { clientListSearchParams } from '../pages/ClientsPage'
import { capabilityForPermission } from '../auth/permissionRegistry'

describe('client list navigation state',()=>{
  it('serializes non-default filters and the one-based page',()=>{
    expect(clientListSearchParams('millensys','INACTIVE','12',2).toString()).toBe('search=millensys&account_status=INACTIVE&status_id=12&page=3')
  })

  it('keeps the default list URL clean',()=>{
    expect(clientListSearchParams('','ACTIVE','',0).toString()).toBe('')
  })

  it('turns an API permission into a secure requestable action',()=>{
    expect(capabilityForPermission('contract.manage')).toEqual({permission:'contract.manage',capability:'Contract manage',module:'Support Hub',resource:'action:contract.manage'})
  })
})
