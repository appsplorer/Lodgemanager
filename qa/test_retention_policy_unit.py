import importlib.util
from datetime import date
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'backend' / 'platform_core' / 'domain' / 'retention.py'


def load_module():
    spec=importlib.util.spec_from_file_location('retention_under_test',MODULE_PATH)
    module=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class RetentionPolicyTests(unittest.TestCase):
    def test_configurable_categories_are_bounded_and_protected_categories_are_fixed(self):
        retention=load_module();policy=retention.normalize_retention_policy({'documents_years':3,'generated_reports_years':2,'communications_years':4,'inactive_members_years':7,'audit_years':1,'finance_years':1})
        self.assertEqual(policy['documents_years'],3)
        self.assertEqual(policy['audit'],'preserve')
        self.assertEqual(policy['finance'],'preserve')
        self.assertNotIn('audit_years',policy)

    def test_invalid_or_dangerously_short_retention_is_rejected(self):
        retention=load_module()
        for value in (0,-1,51,'not-a-number'):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'invalid_retention_years'):
                retention.normalize_retention_policy({'documents_years':value})

    def test_cutoff_is_calendar_safe(self):
        retention=load_module()
        self.assertEqual(retention.retention_cutoff(date(2024,2,29),1),date(2023,2,28))

    def test_generated_document_files_share_document_retention_lifecycle(self):
        source=(ROOT/'backend'/'platform_core'/'tasks.py').read_text(encoding='utf-8')
        self.assertIn('GeneratedDocument',source)
        self.assertIn("retention.generated_document.deleted",source)
        self.assertIn("summary['generated_documents']",source)


if __name__=='__main__':
    unittest.main()
