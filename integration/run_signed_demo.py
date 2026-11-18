#!/usr/bin/env python3
"""Run a local signed-message verification example with a fresh throwaway key."""
import json
import pathlib
import secrets
import sys
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from integration.signed_instruction import sign_instruction, sender_id, verify_instruction

DOMAIN = "billguard.qorechain.test"
CHAIN_ID = 9800
RECIPIENT = "0x1111111111111111111111111111111111111111"


def main():
    now = int(time.time())
    key = Ed25519PrivateKey.generate()  # ephemeral demo key; never persisted
    sender = sender_id(key.public_key())
    envelope = sign_instruction(
        key, domain=DOMAIN, chain_id=CHAIN_ID,
        nonce=secrets.token_urlsafe(24), issued_at=now, expires_at=now + 300,
        recipient=RECIPIENT, value_uqor=100_000, max_fee_uqor=10_000,
    )
    seen = set()
    verified = verify_instruction(
        envelope, expected_sender=sender, expected_domain=DOMAIN,
        expected_chain_id=CHAIN_ID, now=now, seen_nonces=seen,
    )
    print(json.dumps({
        "result": "verified locally",
        "sender": verified.sender,
        "domain": verified.domain,
        "chain_id": verified.chain_id,
        "recipient": verified.recipient,
        "value_uqor": verified.value_uqor,
        "max_fee_uqor": verified.max_fee_uqor,
        "signature_scheme": "Ed25519 (classical; not post-quantum)",
        "network_write": False,
        "private_key_saved": False,
    }, indent=2))


if __name__ == "__main__":
    main()
