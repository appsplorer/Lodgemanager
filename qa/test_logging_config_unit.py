from __future__ import annotations

import importlib.util
import json
import logging
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LoggingConfigTests(unittest.TestCase):
    def test_obs_001_formatter_emits_valid_json_for_untrusted_message_text(self):
        path = ROOT / 'backend/platform_core/logging.py'
        spec = importlib.util.spec_from_file_location('lodgeflow_logging_under_test', path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        record = logging.LogRecord('lodgeflow.test', logging.WARNING, __file__, 1, 'quoted "%s"\nnext', ('value',), None)
        record.request_id = 'request-123'

        payload = json.loads(module.JsonFormatter().format(record))

        self.assertEqual(payload['severity'], 'WARNING')
        self.assertEqual(payload['message'], 'quoted "value"\nnext')
        self.assertEqual(payload['request_id'], 'request-123')
        self.assertNotIn('args', payload)


if __name__ == '__main__':
    unittest.main()
