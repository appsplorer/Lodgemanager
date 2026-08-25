import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'backend' / 'platform_core' / 'domain' / 'report_policy.py'


def load_module():
    spec = importlib.util.spec_from_file_location('report_policy_under_test', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ReportPolicyTests(unittest.TestCase):
    def test_view_export_and_admin_actions_are_distinct(self):
        policy = load_module()
        self.assertEqual(policy.permission_for_report_action('catalog'), 'reports.view')
        self.assertEqual(policy.permission_for_report_action('preview'), 'reports.view')
        self.assertEqual(policy.permission_for_report_action('generate'), 'reports.export')
        self.assertEqual(policy.permission_for_report_action('download'), 'reports.export')
        self.assertEqual(policy.permission_for_report_action('schedule'), 'reports.admin')

    def test_unknown_action_is_rejected(self):
        policy = load_module()
        with self.assertRaisesRegex(ValueError, 'unknown_report_action'):
            policy.permission_for_report_action('publish_everything')

    def test_platform_report_ids_never_enter_tenant_context(self):
        policy = load_module()
        self.assertTrue(policy.report_context_allowed('R-080', platform=True))
        self.assertFalse(policy.report_context_allowed('R-080', platform=False))
        self.assertTrue(policy.report_context_allowed('R-010', platform=False))
        self.assertFalse(policy.report_context_allowed('R-010', platform=True))

    def test_platform_reports_use_least_privilege_control_plane_permissions(self):
        policy = load_module()
        self.assertEqual(policy.platform_permission_for_report('R-080'), 'tenants.view')
        self.assertEqual(policy.platform_permission_for_report('R-081'), 'billing.view')
        self.assertEqual(policy.platform_permission_for_report('R-082'), 'logs.view')
        with self.assertRaisesRegex(ValueError, 'not_a_platform_report'):
            policy.platform_permission_for_report('R-010')


if __name__ == '__main__':
    unittest.main()
