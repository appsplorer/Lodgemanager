import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'backend' / 'platform_core' / 'domain' / 'report_contracts.py'


def load_module():
    spec = importlib.util.spec_from_file_location('report_contracts_under_test', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ReportContractTests(unittest.TestCase):
    def test_every_commercial_report_has_a_minimum_column_contract(self):
        contracts = load_module()
        expected = {
            'R-001','R-002','R-003','R-010','R-011','R-012','R-013','R-014',
            'R-020','R-021','R-030','R-031','R-032','R-033','R-040','R-041',
            'R-042','R-043','R-044','R-050','R-051','R-052','R-053','R-054',
            'R-055','R-056','R-057','R-060','R-061','R-070','R-071','R-072',
            'R-073','R-080','R-081','R-082','R-083','R-084',
        }
        self.assertEqual(set(contracts.REPORT_REQUIRED_COLUMNS), expected)

    def test_contract_rejects_missing_columns_and_malformed_rows(self):
        contracts = load_module()
        with self.assertRaisesRegex(ValueError, 'report_contract_missing_columns'):
            contracts.validate_report_output('R-055', ['Receipt'], [['ABC']])
        with self.assertRaisesRegex(ValueError, 'report_contract_row_width'):
            contracts.validate_report_output('R-055', ['Field', 'Value'], [['Receipt']])

    def test_contract_accepts_empty_result_with_complete_metadata_columns(self):
        contracts = load_module()
        contracts.validate_report_output('R-055', ['Field', 'Value'], [])


if __name__ == '__main__':
    unittest.main()
