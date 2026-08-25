import unittest


class SecurityBoundaryUnitTests(unittest.TestCase):
    """SEC-002/SEC-004/SEC-006: proxy, throttling and URL boundaries."""

    def test_sec_002_untrusted_peer_cannot_spoof_forwarded_client(self):
        from backend.platform_core.services.client_ip import resolve_client_ip

        self.assertEqual(
            resolve_client_ip("198.51.100.8", "203.0.113.9", ["172.16.0.0/12"]),
            "198.51.100.8",
        )

    def test_sec_002_trusted_proxy_chain_returns_nearest_untrusted_hop(self):
        from backend.platform_core.services.client_ip import resolve_client_ip

        self.assertEqual(
            resolve_client_ip(
                "172.18.0.4",
                "192.0.2.250, 203.0.113.42, 172.18.0.3",
                ["172.16.0.0/12"],
            ),
            "203.0.113.42",
        )

    def test_sec_004_critical_rate_limit_stays_bounded_when_cache_fails(self):
        from backend.platform_core.services.rate_limit import LocalRateLimiter, allow

        class BrokenCache:
            def add(self, *args, **kwargs):
                raise ConnectionError("redis unavailable")

        limiter = LocalRateLimiter(max_keys=10)
        outcomes = [allow("login:client", 2, 60, critical=True, cache_backend=BrokenCache(), fallback=limiter, now=100.0) for _ in range(3)]
        self.assertEqual(outcomes, [True, True, False])

    def test_sec_006_public_urls_reject_script_credentials_and_controls(self):
        from backend.platform_core.services.safe_urls import UnsafeURLError, validate_public_url

        for value in ["javascript:alert(1)", "https://user:pass@example.test/path", "https://example.test/\nheader"]:
            with self.subTest(value=value), self.assertRaises(UnsafeURLError):
                validate_public_url(value)
        self.assertEqual(validate_public_url("/members?status=active"), "/members?status=active")
        self.assertEqual(validate_public_url("https://example.test/path"), "https://example.test/path")


if __name__ == "__main__":
    unittest.main()
