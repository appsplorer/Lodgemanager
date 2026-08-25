"""Single source of truth for report action and context authorization."""

ACTION_PERMISSIONS = {
    'catalog': 'reports.view',
    'preview': 'reports.view',
    'history': 'reports.view',
    'saved_view': 'reports.view',
    'generate': 'reports.export',
    'download': 'reports.export',
    'schedule': 'reports.admin',
}

PLATFORM_REPORT_IDS = frozenset({'R-080', 'R-081', 'R-082', 'R-083', 'R-084'})
PLATFORM_REPORT_PERMISSIONS = {
    'R-080': 'tenants.view',
    'R-081': 'billing.view',
    'R-082': 'logs.view',
    'R-083': 'logs.view',
    'R-084': 'logs.view',
}


def permission_for_report_action(action: str) -> str:
    try:
        return ACTION_PERMISSIONS[str(action)]
    except KeyError as exc:
        raise ValueError('unknown_report_action') from exc


def report_context_allowed(report_id: str, *, platform: bool) -> bool:
    is_platform_report = str(report_id).upper() in PLATFORM_REPORT_IDS
    return is_platform_report == bool(platform)


def platform_permission_for_report(report_id: str) -> str:
    try:
        return PLATFORM_REPORT_PERMISSIONS[str(report_id).upper()]
    except KeyError as exc:
        raise ValueError('not_a_platform_report') from exc
