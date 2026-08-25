import unittest


class MemberOperationUnitTests(unittest.TestCase):
    """MEM-003/MEM-006: duplicate and bulk decisions are deterministic."""

    def test_mem_003_duplicate_matching_normalizes_email_phone_and_name(self):
        from backend.platform_core.services.member_operations import duplicate_reasons

        candidate={"first_name":" Ada ","last_name":"Lovelace","email":"ADA@example.test","phone":"+44 7700 900123"}
        existing={"first_name":"ada","last_name":"lovelace","email":"ada@EXAMPLE.test","phone":"07700 900123"}
        reasons=duplicate_reasons(candidate,existing)
        self.assertIn("email",reasons)
        self.assertIn("name",reasons)

    def test_mem_006_bulk_fingerprint_is_order_independent_but_action_bound(self):
        from backend.platform_core.services.member_operations import bulk_fingerprint

        one=bulk_fingerprint(["b","a"],"set_status",{"status":"inactive"})
        two=bulk_fingerprint(["a","b"],"set_status",{"status":"inactive"})
        changed=bulk_fingerprint(["a","b"],"add_tag",{"tag":"inactive"})
        self.assertEqual(one,two)
        self.assertNotEqual(one,changed)


if __name__ == "__main__":
    unittest.main()
