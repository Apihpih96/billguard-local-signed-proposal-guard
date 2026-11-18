"""Run an isolated ML-DSA-87 signed-message demo with a throwaway keypair."""
from __future__ import annotations

import secrets
import time

from mldsa_instruction import generate_throwaway_keypair, sender_id, sign_instruction, verify_instruction

DOMAIN = "billguard.qorechain.test"
CHAIN_ID = 9800
RECIPIENT = "0x1111111111111111111111111111111111111111"


def main() -> None:
    public_key, secret_key = generate_throwaway_keypair()
    now = int(time.time())
    envelope = sign_instruction(
        public_key, secret_key, domain=DOMAIN, chain_id=CHAIN_ID,
        nonce=secrets.token_urlsafe(18), issued_at=now, expires_at=now + 300,
        recipient=RECIPIENT, value_uqor=1000, max_fee_uqor=50,
    )
    verified = verify_instruction(
        envelope, expected_sender=sender_id(public_key), expected_domain=DOMAIN,
        expected_chain_id=CHAIN_ID, now=now, seen_nonces=set(),
    )
    print("Local ML-DSA-87 signature verified.")
    print(f"sender: {verified.sender}")
    print(f"domain/chain: {verified.domain} / {verified.chain_id}")
    print(f"recipient: {verified.recipient}")
    print("key material kept in process memory; no network write performed")


if __name__ == "__main__":
    main()
