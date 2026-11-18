import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import unittest
from policy_engine import Policy, Request, State, evaluate
TARGET = "0x1111111111111111111111111111111111111111"
OTHER = "0x2222222222222222222222222222222222222222"
def setup_case(): return Policy(100, 50, 2, 7_500_000, {TARGET}), State()
class PolicyTests(unittest.TestCase):
    def run_req(self, policy, state, **overrides):
        values = dict(sender_authenticated=True, nonce=1, current_block=105, target=TARGET, value_uqor=2_000_000, max_fee_uqor=100_000)
        values.update(overrides)
        return evaluate(policy, state, Request(**values))
    def test_all_limits_allow_one_in_scope_request(self):
        p,s=setup_case(); d=self.run_req(p,s); self.assertTrue(d.allowed); self.assertEqual((d.used_txs,d.reserved_uqor),(1,2_100_000))
    def test_rejects_unauthenticated_without_consuming(self):
        p,s=setup_case(); d=self.run_req(p,s,sender_authenticated=False); self.assertFalse(d.allowed); self.assertIn("authentication",d.reason); self.assertEqual(s.used_txs,0)
    def test_rejects_replayed_nonce(self):
        p,s=setup_case(); self.assertTrue(self.run_req(p,s).allowed); d=self.run_req(p,s); self.assertFalse(d.allowed); self.assertIn("replayed",d.reason)
    def test_rejects_wrong_target(self):
        p,s=setup_case(); d=self.run_req(p,s,target=OTHER); self.assertFalse(d.allowed); self.assertIn("allowlisted",d.reason)
    def test_rejects_before_and_after_window(self):
        p,s=setup_case(); self.assertIn("outside",self.run_req(p,s,current_block=99).reason); self.assertIn("outside",self.run_req(p,s,current_block=150).reason)
    def test_rejects_value_plus_fee_over_budget(self):
        p,s=setup_case(); d=self.run_req(p,s,value_uqor=7_400_000,max_fee_uqor=200_000); self.assertFalse(d.allowed); self.assertIn("budget",d.reason)
    def test_admitted_slots_are_consumed(self):
        p,s=setup_case(); self.assertTrue(self.run_req(p,s,nonce=1).allowed); self.assertTrue(self.run_req(p,s,nonce=2).allowed); d=self.run_req(p,s,nonce=3); self.assertFalse(d.allowed); self.assertIn("transaction limit",d.reason)
    def test_rejects_truthy_nonboolean_authentication_without_consuming(self):
        p, s = setup_case()
        for auth in ("false", 1, None):
            d = self.run_req(p, s, sender_authenticated=auth, nonce=str(auth))
            self.assertFalse(d.allowed)
            self.assertIn("authentication", d.reason)
            self.assertEqual((s.used_txs, s.reserved_uqor), (0, 0))

    def test_rejects_fractional_or_boolean_amounts_without_consuming(self):
        p, s = setup_case()
        for field, value in (("value_uqor", 1.5), ("max_fee_uqor", True),
                             ("current_block", 105.5)):
            d = self.run_req(p, s, nonce=field, **{field: value})
            self.assertFalse(d.allowed)
            self.assertEqual((s.used_txs, s.reserved_uqor), (0, 0))

if __name__ == "__main__": unittest.main(verbosity=2)
