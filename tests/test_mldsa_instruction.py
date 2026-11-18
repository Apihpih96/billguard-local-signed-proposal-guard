from __future__ import annotations

import copy
import secrets
import unittest

from integration.mldsa_instruction import (
    MldsaInstructionError,
    generate_throwaway_keypair,
    sender_id,
    sign_instruction,
    verify_instruction,
)

DOMAIN = "billguard.qorechain.test"
CHAIN_ID = 9800
NOW = 1_800_000_000
RECIPIENT = "0x1111111111111111111111111111111111111111"


class MldsaInstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public_key, cls.secret_key = generate_throwaway_keypair()
        cls.expected_sender = sender_id(cls.public_key)

    def make_envelope(self, *, issued_at=NOW - 2, expires_at=NOW + 300, **overrides):
        fields = dict(
            domain=DOMAIN, chain_id=CHAIN_ID, nonce=secrets.token_urlsafe(18),
            issued_at=issued_at, expires_at=expires_at, recipient=RECIPIENT,
            value_uqor=1200, max_fee_uqor=20,
        )
        fields.update(overrides)
        return sign_instruction(self.public_key, self.secret_key, **fields)

    def verify(self, envelope, *, now=NOW, seen=None, expected_domain=DOMAIN,
               expected_chain_id=CHAIN_ID, expected_sender=None):
        return verify_instruction(
            envelope, expected_sender=expected_sender or self.expected_sender,
            expected_domain=expected_domain, expected_chain_id=expected_chain_id,
            now=now, seen_nonces=set() if seen is None else seen,
        )

    def test_valid_fips204_mldsa87_instruction(self):
        item = self.verify(self.make_envelope())
        self.assertEqual(item.sender, self.expected_sender)
        self.assertEqual(item.domain, DOMAIN)
        self.assertEqual(item.chain_id, CHAIN_ID)
        self.assertEqual(item.recipient, RECIPIENT)

    def test_tampered_signed_payload_is_rejected(self):
        envelope = self.make_envelope()
        envelope["payload"]["value_uqor"] += 1
        with self.assertRaisesRegex(MldsaInstructionError, "signature"):
            self.verify(envelope)

    def test_replayed_nonce_is_rejected(self):
        envelope = self.make_envelope()
        seen = set()
        self.verify(envelope, seen=seen)
        with self.assertRaisesRegex(MldsaInstructionError, "replayed"):
            self.verify(envelope, seen=seen)

    def test_expired_instruction_is_rejected_without_consuming_nonce(self):
        envelope = self.make_envelope(issued_at=NOW - 400, expires_at=NOW - 1)
        seen = set()
        with self.assertRaisesRegex(MldsaInstructionError, "expired"):
            self.verify(envelope, seen=seen)
        self.assertEqual(seen, set())

    def test_wrong_expected_domain_and_chain_are_rejected(self):
        envelope = self.make_envelope()
        with self.assertRaisesRegex(MldsaInstructionError, "domain"):
            self.verify(envelope, expected_domain="other.example")
        with self.assertRaisesRegex(MldsaInstructionError, "chain"):
            self.verify(envelope, expected_chain_id=1)

    def test_rejects_boolean_expected_chain_id_instead_of_matching_chain_one(self):
        envelope = self.make_envelope(chain_id=1)
        with self.assertRaisesRegex(MldsaInstructionError, "integers"):
            self.verify(envelope, expected_chain_id=True)

    def test_rejects_deeply_nested_payload_without_leaking_recursion_error(self):
        envelope = self.make_envelope()
        nested = "leaf"
        for _ in range(1500):
            nested = [nested]
        envelope["payload"]["domain"] = nested
        with self.assertRaisesRegex(MldsaInstructionError, "signature verification failed"):
            self.verify(envelope)

    def test_rejects_malformed_verifier_context(self):
        envelope = self.make_envelope()
        with self.assertRaisesRegex(MldsaInstructionError, "integers"):
            self.verify(envelope, now=True)
        with self.assertRaisesRegex(MldsaInstructionError, "nonce store"):
            self.verify(envelope, seen=[])

    def test_expected_sender_must_match_signing_key(self):
        envelope = self.make_envelope()
        with self.assertRaisesRegex(MldsaInstructionError, "sender"):
            self.verify(envelope, expected_sender="mldsa87:" + "0" * 64)

    def test_tampered_signature_is_rejected(self):
        envelope = self.make_envelope()
        raw = bytearray.fromhex(envelope["signature_hex"])
        raw[-1] ^= 1
        envelope["signature_hex"] = raw.hex()
        with self.assertRaisesRegex(MldsaInstructionError, "signature"):
            self.verify(envelope)


if __name__ == "__main__":
    unittest.main()
