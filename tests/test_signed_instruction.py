import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from policy_engine import Policy, State
from integration.signed_instruction import (
    InstructionError, sign_instruction, sender_id, verify_instruction, verify_and_evaluate,
)

DOMAIN = "billguard.qorechain.test"
CHAIN = 9800
RECIPIENT = "0x1111111111111111111111111111111111111111"
NOW = 1_800_000_000


class SignedInstructionTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.sender = sender_id(self.key.public_key())
        self.seen = set()
        self.envelope = self.make()

    def make(self, **overrides):
        fields = dict(domain=DOMAIN, chain_id=CHAIN, nonce="nonce_0123456789abc", issued_at=NOW - 1,
                      expires_at=NOW + 300, recipient=RECIPIENT, value_uqor=125_000,
                      max_fee_uqor=8_000)
        fields.update(overrides)
        return sign_instruction(self.key, **fields)

    def verify(self, envelope=None, **overrides):
        args = dict(expected_sender=self.sender, expected_domain=DOMAIN,
                    expected_chain_id=CHAIN, now=NOW, seen_nonces=self.seen)
        args.update(overrides)
        return verify_instruction(self.envelope if envelope is None else envelope, **args)

    def test_accepts_valid_domain_chain_sender_expiry_bound_instruction(self):
        result = self.verify()
        self.assertEqual(result.sender, self.sender)
        self.assertEqual(result.chain_id, CHAIN)
        self.assertEqual(result.recipient, RECIPIENT)
        self.assertEqual(result.value_uqor, 125_000)
        self.assertEqual(len(self.seen), 1)

    def test_verified_instruction_flows_into_policy_simulator(self):
        policy = Policy(start_block=100, block_limit=50, tx_limit=1,
                        value_limit_uqor=150_000, allowed_targets={RECIPIENT})
        state = State()
        verified, decision = verify_and_evaluate(
            self.envelope, policy=policy, state=state, expected_sender=self.sender,
            expected_domain=DOMAIN, expected_chain_id=CHAIN, now=NOW, current_block=105,
        )
        self.assertEqual(verified.recipient, RECIPIENT)
        self.assertTrue(decision.allowed)
        self.assertFalse(state.seen_nonces == set())

    def test_signed_instruction_outside_allowlist_is_authenticated_but_denied(self):
        other = "0x2222222222222222222222222222222222222222"
        policy = Policy(start_block=100, block_limit=50, tx_limit=1,
                        value_limit_uqor=150_000, allowed_targets={other})
        verified, decision = verify_and_evaluate(
            self.envelope, policy=policy, state=__import__("policy_engine").State(),
            expected_sender=self.sender, expected_domain=DOMAIN,
            expected_chain_id=CHAIN, now=NOW, current_block=105,
        )
        self.assertEqual(verified.recipient, RECIPIENT)
        self.assertFalse(decision.allowed)
        self.assertIn("allowlisted", decision.reason)

    def test_signature_covers_every_payload_field(self):
        altered = copy.deepcopy(self.envelope)
        altered["payload"]["value_uqor"] += 1
        with self.assertRaisesRegex(InstructionError, "signature"):
            self.verify(altered)

    def test_binds_to_expected_sender(self):
        with self.assertRaisesRegex(InstructionError, "sender"):
            self.verify(expected_sender="ed25519:" + "0" * 64)

    def test_binds_to_application_domain(self):
        with self.assertRaisesRegex(InstructionError, "domain"):
            self.verify(expected_domain="other.app")

    def test_binds_to_chain_id(self):
        with self.assertRaisesRegex(InstructionError, "chain"):
            self.verify(expected_chain_id=9801)

    def test_rejects_boolean_expected_chain_id_instead_of_matching_chain_one(self):
        envelope = self.make(chain_id=1)
        with self.assertRaisesRegex(InstructionError, "integers"):
            self.verify(envelope, expected_chain_id=True)

    def test_rejects_deeply_nested_payload_without_leaking_recursion_error(self):
        altered = copy.deepcopy(self.envelope)
        nested = "leaf"
        for _ in range(1500):
            nested = [nested]
        altered["payload"]["domain"] = nested
        with self.assertRaisesRegex(InstructionError, "signature verification failed"):
            self.verify(altered)

    def test_rejects_malformed_verifier_context(self):
        with self.assertRaisesRegex(InstructionError, "integers"):
            self.verify(now=True)
        with self.assertRaisesRegex(InstructionError, "nonce store"):
            self.verify(seen_nonces=[])

    def test_rejects_expired_instruction(self):
        with self.assertRaisesRegex(InstructionError, "expired"):
            self.verify(self.make(expires_at=NOW))

    def test_rejects_future_issued_instruction(self):
        with self.assertRaisesRegex(InstructionError, "future"):
            self.verify(self.make(issued_at=NOW + 31, expires_at=NOW + 300))

    def test_rejects_lifetime_longer_than_policy(self):
        with self.assertRaisesRegex(InstructionError, "lifetime"):
            self.verify(self.make(issued_at=NOW - 1, expires_at=NOW + 901))

    def test_rejects_replay(self):
        self.verify()
        with self.assertRaisesRegex(InstructionError, "replayed"):
            self.verify()

    def test_rejects_bad_recipient_without_consuming_nonce(self):
        with self.assertRaisesRegex(InstructionError, "recipient"):
            self.verify(self.make(recipient="not-an-address"))
        self.assertEqual(self.seen, set())

    def test_rejects_unknown_or_missing_fields(self):
        altered = copy.deepcopy(self.envelope)
        altered["payload"]["unreviewed"] = True
        with self.assertRaisesRegex(InstructionError, "fields"):
            self.verify(altered)

    def test_rejects_wrong_key_even_if_validly_signed(self):
        other = Ed25519PrivateKey.generate()
        envelope = sign_instruction(other, domain=DOMAIN, chain_id=CHAIN,
            nonce="nonce_0123456789xyz", issued_at=NOW - 1, expires_at=NOW + 300,
            recipient=RECIPIENT, value_uqor=1, max_fee_uqor=1)
        with self.assertRaisesRegex(InstructionError, "sender"):
            self.verify(envelope)


if __name__ == "__main__":
    unittest.main(verbosity=2)
