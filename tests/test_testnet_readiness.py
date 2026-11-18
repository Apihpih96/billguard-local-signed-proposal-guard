import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integration"))
import testnet_readiness as tr

ACCOUNT = "qor1" + "a" * 38


def good_rule(**overrides):
    rule = {
        "id": "safe",
        "enabled": True,
        "per_tx_limit": "1000000",
        "daily_limit": "2000000",
        "allowed_denoms": ["uqor"],
        "denom_limits": [],
    }
    rule.update(overrides)
    return rule


class TestReadiness(unittest.TestCase):
    def test_address_validation_rejects_path_injection_and_wrong_prefix(self):
        tr.validate_account(ACCOUNT)
        for bad in ["QOR1" + "a" * 38, "qor1" + "a" * 37 + "!", "qor1abc", "qor1" + "b" * 38, "qor1" + "1" * 38]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tr.validate_account(bad)

    def test_queries_only_documented_get_paths_for_canonical_account(self):
        seen = []
        fixtures = {
            tr.ENV_PATHS["abstract_account_config"]: {"enabled": True},
            tr.ENV_PATHS["permission_schema"]: {"permissions": ["evm"]},
            tr.ENV_PATHS["evm_limits"]: {"tx_max_gas": 1},
            f"/qorechain/pqc/v1/account/{ACCOUNT}": {"found": True},
            f"/qorechain/pqc/v1/evm_window/{ACCOUNT}": {"found": False},
            f"/qorechain/abstractaccount/v1/accounts/{ACCOUNT}/authenticators": {"authenticators": []},
            f"/qorechain/abstractaccount/v1/accounts/{ACCOUNT}/spending_rules": {"rules": [], "authenticator_rules": []},
        }
        result = tr.inspect(lambda p: (seen.append(p), fixtures[p])[1], account=ACCOUNT, now_unix=100)
        self.assertEqual(set(seen), set(fixtures))
        self.assertTrue(result["http_get_only"])
        self.assertTrue(result["no_chain_write_attempted"])
        self.assertEqual(result["account_specific_readiness"]["pqc_key_status"], "registered")
        self.assertEqual(result["account_specific_readiness"]["evm_window_exists"], False)

    def test_expired_revoked_or_non_evm_authenticator_not_counted(self):
        auths = [
            {"revoked": False, "expiry_unix": 99, "permissions": ["evm"], "has_spend_rule": False},
            {"revoked": True, "expiry_unix": 200, "permissions": ["evm"], "has_spend_rule": False},
            {"revoked": False, "expiry_unix": 200, "permissions": ["send"], "has_spend_rule": False},
        ]
        summary = tr.summarize_account({"found": True}, {"found": False, "authenticators": auths}, {"rules": [good_rule()]}, 100)
        self.assertEqual(summary["active_evm_authenticator_count"], 0)
        self.assertEqual(summary["active_evm_authenticator_with_recognized_positive_uqor_rule_count"], 0)

    def test_positive_account_rule_applies_only_to_auth_without_own_rule(self):
        auths = [
            {"revoked": False, "expiry_unix": 200, "permissions": ["evm"], "has_spend_rule": False},
            {"revoked": False, "expiry_unix": 200, "permissions": ["evm"], "has_spend_rule": True, "pubkey_hex": "01"},
        ]
        rules = {"rules": [good_rule()], "authenticator_rules": []}
        summary = tr.summarize_account({"found": True}, {"found": True, "live": True, "authenticators": auths}, rules, 100)
        self.assertEqual(summary["active_evm_authenticator_with_recognized_positive_uqor_rule_count"], 1)
        self.assertEqual(summary["window"]["live"], True)

    def test_first_enabled_account_rule_is_not_skipped_if_unbounded(self):
        auth = {"revoked": False, "expiry_unix": 200, "permissions": ["evm"], "has_spend_rule": False}
        rules = {"rules": [good_rule(per_tx_limit="0"), good_rule(id="later")], "authenticator_rules": []}
        summary = tr.summarize_account({"found": True}, {"found": False, "authenticators": [auth]}, rules, 100)
        self.assertEqual(summary["active_evm_authenticator_with_recognized_positive_uqor_rule_count"], 0)

    def test_denom_specific_zero_does_not_fall_back_to_base_limit(self):
        auth = {"revoked": False, "expiry_unix": 200, "permissions": ["evm"], "has_spend_rule": False}
        rule = good_rule(denom_limits=[{"denom": "uqor", "per_tx_limit": "0", "daily_limit": "500"}])
        summary = tr.summarize_account({"found": True}, {"found": False, "authenticators": [auth]}, {"rules": [rule], "authenticator_rules": []}, 100)
        self.assertEqual(summary["active_evm_authenticator_with_recognized_positive_uqor_rule_count"], 0)

    def test_unknown_shapes_and_failed_reads_stay_inconclusive(self):
        summary = tr.summarize_account({"found": "true"}, {"found": 1, "authenticators": "bad"}, {"rules": "bad"}, 100)
        self.assertEqual(summary["pqc_key_status"], "unknown")
        self.assertIsNone(summary["evm_window_exists"])
        result = tr.inspect(lambda path: (_ for _ in ()).throw(RuntimeError("HTTP 403")), account=ACCOUNT)
        self.assertEqual(result["readiness"], "inconclusive")
        self.assertTrue(result["no_chain_write_attempted"])
        self.assertEqual(len(result["fetch_errors"]), 7)

    def test_string_unix_expiry_is_compared_without_float_coercion(self):
        auth = {"revoked": False, "expiry_unix": "200", "permissions": ["evm"], "has_spend_rule": False}
        summary = tr.summarize_account({"found": True}, {"found": False, "authenticators": [auth]}, {"rules": [good_rule()]}, 100)
        self.assertEqual(summary["active_evm_authenticator_count"], 1)
        self.assertEqual(summary["active_evm_authenticator_with_recognized_positive_uqor_rule_count"], 1)

    def test_exact_integer_fields_reject_floats_and_booleans(self):
        self.assertEqual(tr._exact_integer("9007199254740993"), "9007199254740993")
        self.assertIsNone(tr._exact_integer(1.5))
        self.assertIsNone(tr._exact_integer(True))


if __name__ == "__main__":
    unittest.main()
