import json
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integration"))
from preflight import assess, get_json
from prepare_plan import build_plan


class PreflightTests(unittest.TestCase):
    def test_enabled_testnet_environment_passes_environment_checks(self):
        result = assess(
            {"config": {"enabled": True}},
            {"permissions": ["send", "evm"]},
            {"tx_max_gas": "30000000"},
        )
        self.assertTrue(result["environment_ready_for_account_specific_review"])
        self.assertFalse(result["account_specific_readiness_checked"])

    def test_missing_evm_permission_fails(self):
        result = assess({"config": {"enabled": True}}, {"permissions": ["send"]}, {"tx_max_gas": "30000000"})
        self.assertFalse(result["checks"]["evm_permission_present"])
        self.assertFalse(result["environment_ready_for_account_specific_review"])

    def test_disabled_aa_or_missing_gas_fails(self):
        result = assess({"config": {"enabled": False}}, {"permissions": ["evm"]}, {"limits": {"tx_max_gas": "0"}})
        self.assertFalse(result["checks"]["abstract_account_enabled"])
        self.assertFalse(result["checks"]["positive_testnet_evm_gas_limit"])

    def test_preflight_rejects_coercible_noninteger_gas_and_malformed_permissions(self):
        base_config = {"config": {"enabled": True}}
        for gas in (True, 1.5, "1.5", " 2", "-1"):
            with self.subTest(gas=gas):
                result = assess(base_config, {"permissions": ["evm"]}, {"tx_max_gas": gas})
                self.assertFalse(result["checks"]["positive_testnet_evm_gas_limit"])
                self.assertFalse(result["environment_ready_for_account_specific_review"])
        for permissions in ("evm", {"evm": True}, ["evm", 1]):
            with self.subTest(permissions=permissions):
                result = assess(base_config, {"permissions": permissions}, {"tx_max_gas": 1})
                self.assertFalse(result["checks"]["evm_permission_present"])
                self.assertFalse(result["environment_ready_for_account_specific_review"])

    def test_preflight_oversized_decimal_gas_string_fails_closed(self):
        result = assess(
            {"config": {"enabled": True}},
            {"permissions": ["evm"]},
            {"tx_max_gas": "9" * 5000},
        )
        self.assertFalse(result["checks"]["positive_testnet_evm_gas_limit"])
        self.assertFalse(result["environment_ready_for_account_specific_review"])

    def test_preflight_handles_malformed_nested_objects_closed(self):
        result = assess({"config": "enabled"}, {"permissions": ["evm"]}, {"limits": []})
        self.assertFalse(result["checks"]["abstract_account_enabled"])
        self.assertFalse(result["checks"]["positive_testnet_evm_gas_limit"])
        self.assertFalse(result["environment_ready_for_account_specific_review"])

    def test_invalid_top_level_gas_limit_is_not_masked_by_nested_value(self):
        result = assess(
            {"config": {"enabled": True}},
            {"permissions": ["evm"]},
            {"tx_max_gas": 0, "limits": {"tx_max_gas": "30000000"}},
        )
        self.assertFalse(result["checks"]["positive_testnet_evm_gas_limit"])
        self.assertFalse(result["environment_ready_for_account_specific_review"])

    def test_preflight_reports_invalid_utf8_as_a_read_error(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b"\xff"
        with patch("preflight.urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "not valid UTF-8"):
                get_json("/test")

    def test_preflight_reports_excessively_nested_json_as_a_read_error(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return (b"[" * 100000) + b"0" + (b"]" * 100000)
        with patch("preflight.urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "nested too deeply"):
                get_json("/test")


class PlanTests(unittest.TestCase):
    def test_plan_is_non_executable_and_has_no_secrets_or_broadcast(self):
        plan = build_plan()
        self.assertEqual(plan["status"], "draft_template_not_executable")
        self.assertFalse(plan["safety"]["broadcast_or_registration_performed"])
        self.assertTrue(plan["safety"]["owner_signed_setup_required"])
        self.assertTrue(plan["safety"]["public_transaction_requires_separate_owner_approval"])
        self.assertIsNone(plan["owner_review_fields"]["owner_qor1_account"])
        encoded = json.dumps(plan).lower()
        self.assertIn("authenticated messaging", encoded)
        self.assertIn("wallet-adapter", encoded)

    def test_plan_pins_testnet_and_separate_limits(self):
        plan = build_plan()
        self.assertEqual(plan["network"]["evm_chain_id"], 9800)
        self.assertIn("window_max_value_uqor_including_max_fee", plan["owner_review_fields"])
        self.assertIn("spending_rule_daily_uqor", plan["owner_review_fields"])
        self.assertEqual(plan["safety"]["no_generic_contract_router"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
