ACTIONS={'view','create','edit','delete','export','approve','admin'}
MODULES={'dashboard','members','officers','candidates','meetings','dues','finance','documents','communications','reports','audit','settings'}
ALL_PERMISSION_PRIMITIVES={f'{module}.{action}' for module in MODULES for action in ACTIONS}

ROLE_PERMISSIONS={
 'owner':{'*'},
 'admin':{'*'},
 'secretary':{'dashboard.view','members.view','members.create','members.edit','members.export','officers.view','officers.edit','candidates.view','candidates.edit','meetings.view','meetings.create','meetings.edit','meetings.approve','documents.view','documents.create','documents.edit','communications.view','communications.create','communications.edit','reports.view','reports.export','reports.admin','audit.view','settings.view'},
 'treasurer':{'dashboard.view','members.view','dues.view','dues.edit','dues.admin','finance.view','finance.edit','finance.approve','finance.export','reports.view','reports.export','reports.admin','documents.view','settings.view'},
 'membership':{'dashboard.view','members.view','members.create','members.edit','members.export','candidates.view','candidates.edit','reports.view','settings.view'},
 'mentor':{'dashboard.view','members.view','candidates.view','candidates.edit','meetings.view','documents.view'},
 'document_manager':{'dashboard.view','documents.view','documents.create','documents.edit','documents.delete','members.view','meetings.view'},
 'auditor':{'dashboard.view','members.view','officers.view','candidates.view','meetings.view','dues.view','finance.view','documents.view','reports.view','reports.export','audit.view','settings.view'},
 'viewer':{'dashboard.view','members.view','officers.view','candidates.view','meetings.view','dues.view','finance.view','documents.view','reports.view','settings.view'},
 'custom':set(),
}
ALIASES={'communications.admin':'communications.edit','finance.export':'reports.export','dues.create':'dues.edit','finance.create':'finance.edit'}
ALL_PERMISSION_PRIMITIVES.update(ALIASES)
ALL_PERMISSION_PRIMITIVES.update(ALIASES.values())


def effective_custom_permissions(membership):
    """Resolve tenant custom-role permissions dynamically on every request.

    Memberships linked to a saved CustomRoleDefinition inherit its current permission
    bundle, so role edits take effect immediately without stale authorization caches.
    Legacy per-membership custom permissions remain supported for non-custom roles.
    """
    if not membership:
        return []
    custom_role=getattr(membership,'custom_role',None)
    if getattr(membership,'role',None)=='custom' and custom_role is not None:
        return list(custom_role.permissions or [])
    return list(getattr(membership,'custom_permissions',[]) or [])


def normalize_permission(permission):
 return ALIASES.get(str(permission),str(permission))


def has_permission(role,permission,custom_permissions=None):
 p=normalize_permission(permission);allowed=ROLE_PERMISSIONS.get(role,set());custom={normalize_permission(x) for x in (custom_permissions or []) if isinstance(x,str)}
 return '*' in allowed or p in allowed or p in custom


def validate_permission_list(permissions):
 if not isinstance(permissions,list):
  raise ValueError('permissions_must_be_list')
 cleaned=[]
 for raw in permissions:
  if not isinstance(raw,str): raise ValueError('permission_must_be_string')
  permission=raw.strip()
  if not permission or permission=='*' or permission not in ALL_PERMISSION_PRIMITIVES:
   raise ValueError(f'unknown_or_unsafe_permission:{permission}')
  normalized=normalize_permission(permission)
  if normalized not in cleaned: cleaned.append(normalized)
 return cleaned


def ensure_grantable_permissions(assigner_role,assigner_custom,requested_permissions):
 """Validate custom permission primitives and prevent privilege escalation.

 Owners/admins may grant any documented tenant permission primitive. Other roles may only
 grant permissions they already hold, even if future workflows expose delegated role editing.
 """
 requested=validate_permission_list(requested_permissions)
 allowed=ROLE_PERMISSIONS.get(assigner_role,set())
 if '*' in allowed: return requested
 for permission in requested:
  if not has_permission(assigner_role,permission,assigner_custom):
   raise PermissionError(f'cannot_grant_permission:{permission}')
 return requested
