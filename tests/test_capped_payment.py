import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integration"))
from capped_payment import build_capped_plan
from run_capped_demo import PAYMENT, WINDOW, SPENDING_RULE


class CappedPaymentTests(unittest.TestCase):
    def setUp(self):
        self.payment = dict(PAYMENT)
        self.window = dict(WINDOW)
        self.rule = dict(SPENDING_RULE)

    def build(self):
        return build_capped_plan(self.payment, self.window, self.rule)

    def test_synthetic_one_recipient_native_payment_fits_all_separate_caps(self):
        result = self.build()
        self.assertEqual(result["status"], "local_plan_passes_simulated_caps")
        self.assertEqual(result["payment"]["worst_case_outflow_uqor"], 1_100_000)
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["execution"]["signing_performed"])
        self.assertFalse(result["execution"]["authorization_window_opened"])
        self.assertFalse(result["execution"]["broadcast_performed"])
        self.assertFalse(result["execution"]["executable"])

    def test_over_cap_includes_fee(self):
        self.window["max_value_uqor"] = 1_099_999
        with self.assertRaisesRegex(ValueError, "amount plus maximum fee"):
            self.build()

    def test_per_tx_and_daily_rules_are_independent_caps(self):
        self.rule["per_tx_uqor"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "per-transaction cap"):
            self.build()
        self.rule["per_tx_uqor"] = 1_100_000
        self.rule["daily_uqor"] = 1_099_999
        with self.assertRaisesRegex(ValueError, "daily cap"):
            self.build()

    def test_recipient_must_match_one_allowlisted_target(self):
        self.payment["recipient"] = "0x3333333333333333333333333333333333333333"
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.build()

    def test_rejects_multiple_transactions_or_missing_native_only(self):
        self.window["max_txs"] = 2
        with self.assertRaisesRegex(ValueError, "one-transaction"):
            self.build()
        self.window["max_txs"] = 1
        self.window["native_only"] = False
        with self.assertRaisesRegex(ValueError, "native_only=true"):
            self.build()

    def test_rejects_calldata_and_non_native_denom(self):
        self.payment["calldata"] = "0x1234"
        with self.assertRaisesRegex(ValueError, "calldata"):
            self.build()
        self.payment["calldata"] = "0x"
        self.payment["denom"] = "erc20"
        with self.assertRaisesRegex(ValueError, "native uqor"):
            self.build()

    def test_rejects_invalid_amounts_addresses_ranges_and_unknown_fields(self):
        self.payment["amount_uqor"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.build()
        self.payment = dict(PAYMENT)
        self.payment["sender"] = "qor1private"
        with self.assertRaisesRegex(ValueError, "20-byte EVM address"):
            self.build()
        self.payment = dict(PAYMENT)
        self.window["blocks"] = 17_281
        with self.assertRaisesRegex(ValueError, "1..17280"):
            self.build()
        self.window = dict(WINDOW)
        self.rule["secret"] = "must-not-be-accepted"
        with self.assertRaisesRegex(ValueError, "exactly the documented fields"):
            self.build()

    def test_rejects_nonobject_inputs_without_crashing(self):
        for field in ("payment", "window", "rule"):
            with self.subTest(field=field):
                args = [dict(PAYMENT), dict(WINDOW), dict(SPENDING_RULE)]
                index = {"payment": 0, "window": 1, "rule": 2}[field]
                args[index] = None
                with self.assertRaisesRegex(ValueError, "must be an object"):
                    build_capped_plan(*args)

    def test_requires_one_allowlisted_recipient_and_enabled_rule(self):
        self.window["allowed_targets"] = []
        with self.assertRaisesRegex(ValueError, "exactly one allowed target"):
            self.build()
        self.window = dict(WINDOW)
        self.rule["enabled"] = False
        with self.assertRaisesRegex(ValueError, "must be enabled"):
            self.build()


if __name__ == "__main__":
    unittest.main(verbosity=2)
