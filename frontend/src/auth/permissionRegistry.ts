export type ProtectedCapability = { permission: string; capability: string; module: string; resource: string }

export const permissionRegistry: Record<string, ProtectedCapability> = {
  '/access-requests': { permission: 'permission.grant.in_context', capability: 'Review in-context access requests', module: 'Identity and access', resource: '/access-requests' },
  '/profiles': { permission: 'profile.manage', capability: 'Manage profiles and privileges', module: 'Identity and access', resource: '/profiles' },
  '/users': { permission: 'user.manage', capability: 'Manage users', module: 'Identity and access', resource: '/users' },
  '/audit': { permission: 'audit.view', capability: 'View immutable audit evidence', module: 'Audit', resource: '/audit' },
  '/financial': { permission: 'finance.view', capability: 'View financial operations', module: 'Finance', resource: '/financial' },
  '/tickets/create': { permission: 'ticket.create', capability: 'Create support tickets', module: 'Tickets', resource: '/tickets/create' },
  '/field-visits/create': { permission: 'visit.field.create.self', capability: 'Request a field visit', module: 'Visits', resource: '/field-visits/create' },
  '/clients': { permission: 'client.view', capability: 'View clients', module: 'CRM', resource: '/clients' },
  '/portal/profile': { permission: 'portal.client_profile.view', capability: 'View client portal profile', module: 'Client portal', resource: '/portal/profile' },
  '/contracts': { permission: 'contract.view', capability: 'Open Contract Workspace', module: 'Contracts', resource: '/contracts' },
  'action:contract-notification-rules': { permission: 'contract.notification_rules.manage', capability: 'Configure contract expiration notifications', module: 'Contracts', resource: 'action:contract.notification_rules.manage' },
  '/internal-operations': { permission: 'internal_operation.workspace.view', capability: 'Open Operations Workspace', module: 'Operations', resource: '/internal-operations' },
  '/project-handovers': { permission: 'project_handover.view', capability: 'Open Project Handovers', module: 'Project delivery', resource: '/project-handovers' },
  'action:project-handover-edit': { permission: 'project_handover.edit_pending', capability: 'Edit draft and pending project handovers', module: 'Project delivery', resource: 'action:project_handover.edit_pending' },
}

export function capabilityForPath(pathname: string) {
  return permissionRegistry[pathname] ?? Object.values(permissionRegistry).find(item => pathname.startsWith(`${item.resource}/`))
}

export function capabilityForPermission(permission:string):ProtectedCapability {
  const registered=Object.values(permissionRegistry).find(item=>item.permission===permission)
  if(registered)return registered
  const words=permission.replaceAll('_',' ').replaceAll('.',' ')
  return {permission,capability:words.charAt(0).toUpperCase()+words.slice(1),module:'Support Hub',resource:`action:${permission}`}
}
