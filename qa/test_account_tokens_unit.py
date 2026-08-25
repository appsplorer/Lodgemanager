from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest


class AccountTokenDomainTests(unittest.TestCase):
    """IAM-004/IAM-005: account links are opaque, expiring and single-use."""

    def test_iam_004_token_digest_is_stable_without_storing_raw_token(self):
        from backend.platform_core.services.account_tokens import digest_token, new_raw_token

        raw = new_raw_token()
        self.assertGreaterEqual(len(raw), 43)
        self.assertEqual(len(digest_token(raw)), 64)
        self.assertEqual(digest_token(raw), digest_token(raw))
        self.assertNotIn(raw, digest_token(raw))

    def test_iam_004_invitation_rejects_consumed_record(self):
        from backend.platform_core.services.account_tokens import AccountTokenError, validate_token_record

        now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
        record = SimpleNamespace(
            digest="ignored",
            purpose="invitation",
            expires_at=now + timedelta(minutes=5),
            consumed_at=now - timedelta(seconds=1),
        )
        with self.assertRaisesRegex(AccountTokenError, "token_already_used"):
            validate_token_record(record, "raw", "invitation", now=now, digest=lambda value: "ignored")

    def test_iam_004_invitation_rejects_expired_record_at_boundary(self):
        from backend.platform_core.services.account_tokens import AccountTokenError, validate_token_record

        now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
        record = SimpleNamespace(digest="expected", purpose="invitation", expires_at=now, consumed_at=None)
        with self.assertRaisesRegex(AccountTokenError, "token_expired"):
            validate_token_record(record, "raw", "invitation", now=now, digest=lambda value: "expected")

    def test_iam_005_reset_rejects_wrong_purpose_or_digest(self):
        from backend.platform_core.services.account_tokens import AccountTokenError, validate_token_record

        now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
        record = SimpleNamespace(digest="expected", purpose="password_reset", expires_at=now + timedelta(minutes=5), consumed_at=None)
        with self.assertRaisesRegex(AccountTokenError, "token_purpose_mismatch"):
            validate_token_record(record, "raw", "invitation", now=now, digest=lambda value: "expected")
        with self.assertRaisesRegex(AccountTokenError, "invalid_token"):
            validate_token_record(record, "raw", "password_reset", now=now, digest=lambda value: "wrong")


if __name__ == "__main__":
    unittest.main()
