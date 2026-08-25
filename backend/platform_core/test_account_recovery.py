import json
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .models import AccountActionToken, Tenant, TenantMembership


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    FRONTEND_BASE_URL="https://app.example.test",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountRecoveryIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner@example.test",
            email="owner@example.test",
            password="Owner-Strong-Pass-123!",
        )
        self.tenant = Tenant.objects.create(name="Recovery Lodge", slug="recovery-lodge")
        TenantMembership.objects.create(user=self.owner, tenant=self.tenant, role="owner")
        self.client.force_login(self.owner)
        self.headers = {"HTTP_X_LODGE_ID": str(self.tenant.id)}

    @staticmethod
    def _token_from_last_email():
        match = re.search(r"[?&]token=([^\s&]+)", mail.outbox[-1].body)
        if not match:
            raise AssertionError(mail.outbox[-1].body)
        return match.group(1)

    def test_iam_004_invitation_is_single_use_and_applies_password_policy(self):
        invited = self.client.post(
            "/api/settings/users",
            data=json.dumps({"email": "invitee@example.test", "role": "viewer", "send_invite": True}),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(invited.status_code, 201)
        self.assertTrue(invited.json()["invite_sent"])
        token = self._token_from_last_email()
        self.client.logout()

        weak = self.client.post(
            "/api/auth/invitation",
            data=json.dumps({"token": token, "password": "password"}),
            content_type="application/json",
        )
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(weak.json()["error"], "password_policy")

        accepted = self.client.post(
            "/api/auth/invitation",
            data=json.dumps({"token": token, "password": "Invitation-Strong-Pass-123!"}),
            content_type="application/json",
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(accepted.json()["ok"])

        replay = self.client.post(
            "/api/auth/invitation",
            data=json.dumps({"token": token, "password": "Another-Strong-Pass-123!"}),
            content_type="application/json",
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.json()["error"], "token_already_used")
        self.assertEqual(AccountActionToken.objects.filter(purpose="invitation", consumed_at__isnull=False).count(), 1)

    def test_iam_005_password_reset_request_is_enumeration_safe_and_token_is_single_use(self):
        self.client.logout()
        existing = self.client.post(
            "/api/auth/password-reset/request",
            data=json.dumps({"email": self.owner.email}),
            content_type="application/json",
        )
        missing = self.client.post(
            "/api/auth/password-reset/request",
            data=json.dumps({"email": "missing@example.test"}),
            content_type="application/json",
        )
        self.assertEqual(existing.status_code, 202)
        self.assertEqual(missing.status_code, 202)
        self.assertEqual(existing.json(), missing.json())
        token = self._token_from_last_email()

        reset = self.client.post(
            "/api/auth/password-reset/confirm",
            data=json.dumps({"token": token, "password": "Reset-Strong-Pass-456!"}),
            content_type="application/json",
        )
        self.assertEqual(reset.status_code, 200)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password("Reset-Strong-Pass-456!"))

        replay = self.client.post(
            "/api/auth/password-reset/confirm",
            data=json.dumps({"token": token, "password": "Reset-Strong-Pass-789!"}),
            content_type="application/json",
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.json()["error"], "token_already_used")
