from __future__ import annotations

import unittest

from backend.platform_core.domain.job_policy import retry_delay, retryable_job


class JobPolicyTests(unittest.TestCase):
    def test_job_003_retry_delay_is_exponential_and_bounded(self):
        self.assertEqual([retry_delay(attempt, base=30, cap=300) for attempt in range(1, 6)], [30, 60, 120, 240, 300])
        self.assertEqual(retry_delay(99, base=30, cap=300), 300)

    def test_job_004_only_well_formed_allowlisted_jobs_are_retryable(self):
        self.assertTrue(retryable_job('member_import', {'actor_id': 7, 'rows': []}))
        self.assertTrue(retryable_job('scheduled_report', {'schedule_id': '123'}))
        self.assertTrue(retryable_job('retention_enforcement', {'dry_run': True}))
        self.assertFalse(retryable_job('scheduled_report', {}))
        self.assertFalse(retryable_job('member_import', {'rows': []}))
        self.assertFalse(retryable_job('send_money', {'actor_id': 7}))


if __name__ == '__main__':
    unittest.main()
