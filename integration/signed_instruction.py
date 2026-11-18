"""Local Ed25519 signed-instruction verifier for the BillGuard demo.

This is a message-authentication simulation, not a QoreChain authenticator client,
not ML-DSA, and not a post-quantum signature. Nonce storage is caller-owned and
in-memory in this demo; production needs durable, atomic replay protection.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import MutableSet
from dataclasses import dataclass

from policy_engine import Decision, Policy, Request, State, evaluate

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PAYLOAD_FIELDS = {
    "version", "domain", "chain_id", "sender", "nonce", "issued_at", "expires_at",
    "action", "recipient", "value_uqor", "max_fee_uqor",
}
ENVELOPE_FIELDS = {"payload", "public_key_hex", "signature_hex"}
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
MAX_U256 = (1 << 256) - 1


class InstructionError(ValueError):
    """A signed instruction failed authentication or context checks."""


@dataclass(frozen=True)
class VerifiedInstruction:
    sender: str
    domain: str
    chain_id: int
    nonce: str
    issued_at: int
    expires_at: int
    action: str
    recipient: str
    value_uqor: int
    max_fee_uqor: int


def sender_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return "ed25519:" + hashlib.sha256(raw).hexdigest()


def _canonical_payload(payload: dict) -> bytes:
    """One deterministic byte representation; only JSON-compatible exact fields."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def sign_instruction(private_key: Ed25519PrivateKey, *, domain: str, chain_id: int,
                      nonce: str, issued_at: int, expires_at: int, recipient: str,
                      value_uqor: int, max_fee_uqor: int) -> dict:
    """Create an envelope. Callers should use a throwaway key in this local demo."""
    public_key = private_key.public_key()
    payload = {
        "version": 1,
        "domain": domain,
        "chain_id": chain_id,
        "sender": sender_id(public_key),
        "nonce": nonce,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "action": "pay_qor",
        "recipient": recipient,
        "value_uqor": value_uqor,
        "max_fee_uqor": max_fee_uqor,
    }
    raw_public = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "payload": payload,
        "public_key_hex": raw_public.hex(),
        "signature_hex": private_key.sign(_canonical_payload(payload)).hex(),
    }


def verify_instruction(envelope: dict, *, expected_sender: str, expected_domain: str,
                       expected_chain_id: int, now: int, seen_nonces: MutableSet[str],
                       max_ttl_seconds: int = 900, clock_skew_seconds: int = 30) -> VerifiedInstruction:
    """Authenticate and context-check an instruction; consume its nonce on success.

    The sender identity is derived from the signing public key and must also match
    the caller's configured expected_sender. A nonce is consumed only after all
    cryptographic/context/schema checks pass. This function does not persist it.
    """
    if not isinstance(expected_sender, str) or not isinstance(expected_domain, str):
        raise InstructionError("invalid verifier identity context")
    if type(expected_chain_id) is not int or type(now) is not int:
        raise InstructionError("chain id and current time must be integers")
    if (type(max_ttl_seconds) is not int or max_ttl_seconds <= 0
            or type(clock_skew_seconds) is not int or clock_skew_seconds < 0):
        raise InstructionError("invalid verifier time policy")
    if not isinstance(seen_nonces, MutableSet):
        raise InstructionError("nonce store must be a mutable set")
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
        raise InstructionError("invalid envelope fields")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS:
        raise InstructionError("invalid instruction fields")
    pub_hex, sig_hex = envelope.get("public_key_hex"), envelope.get("signature_hex")
    if not isinstance(pub_hex, str) or not isinstance(sig_hex, str):
        raise InstructionError("invalid key or signature encoding")
    try:
        pub_bytes, sig_bytes = bytes.fromhex(pub_hex), bytes.fromhex(sig_hex)
        if len(pub_bytes) != 32 or len(sig_bytes) != 64:
            raise ValueError("wrong length")
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, _canonical_payload(payload))
    except (ValueError, InvalidSignature, TypeError, json.JSONDecodeError, RecursionError) as exc:
        raise InstructionError("signature verification failed") from exc

    # Validate types strictly: bool is an int subclass in Python.
    if type(payload["version"]) is not int or payload["version"] != 1:
        raise InstructionError("unsupported protocol version")
    if not isinstance(payload["domain"], str) or payload["domain"] != expected_domain:
        raise InstructionError("wrong application domain")
    if type(payload["chain_id"]) is not int or payload["chain_id"] != expected_chain_id:
        raise InstructionError("wrong chain")
    derived_sender = sender_id(public_key)
    if payload["sender"] != derived_sender or derived_sender != expected_sender:
        raise InstructionError("wrong sender")
    nonce = payload["nonce"]
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        raise InstructionError("invalid nonce")
    issued, expires = payload["issued_at"], payload["expires_at"]
    if type(issued) is not int or type(expires) is not int:
        raise InstructionError("invalid instruction times")
    if issued > now + clock_skew_seconds:
        raise InstructionError("instruction issued in the future")
    if expires <= now or expires <= issued:
        raise InstructionError("instruction expired or has invalid expiry")
    if expires - issued > max_ttl_seconds:
        raise InstructionError("instruction lifetime exceeds policy")
    if payload["action"] != "pay_qor":
        raise InstructionError("unsupported action")
    recipient = payload["recipient"]
    if not isinstance(recipient, str) or not ADDRESS_RE.fullmatch(recipient):
        raise InstructionError("invalid recipient")
    for field in ("value_uqor", "max_fee_uqor"):
        value = payload[field]
        if type(value) is not int or not 0 <= value <= MAX_U256:
            raise InstructionError(f"invalid {field}")
    replay_key = f"{derived_sender}:{nonce}"
    if replay_key in seen_nonces:
        raise InstructionError("replayed instruction nonce")
    seen_nonces.add(replay_key)
    return VerifiedInstruction(
        sender=derived_sender, domain=payload["domain"], chain_id=payload["chain_id"],
        nonce=nonce, issued_at=issued, expires_at=expires, action=payload["action"],
        recipient=recipient, value_uqor=payload["value_uqor"],
        max_fee_uqor=payload["max_fee_uqor"],
    )


def verify_and_evaluate(envelope: dict, *, policy: Policy, state: State,
                        expected_sender: str, expected_domain: str,
                        expected_chain_id: int, now: int, current_block: int):
    """Verify a signed instruction, then pass it through the local policy simulator.

    The signature proves only that the throwaway/configured Ed25519 key signed this
    local message. The subsequent allow/deny decision is still Python simulation,
    not chain validation or an on-chain spending-rule result.
    """
    verified = verify_instruction(
        envelope, expected_sender=expected_sender, expected_domain=expected_domain,
        expected_chain_id=expected_chain_id, now=now, seen_nonces=state.seen_nonces,
    )
    request = Request(
        sender_authenticated=True, nonce=verified.nonce, current_block=current_block,
        target=verified.recipient, value_uqor=verified.value_uqor,
        max_fee_uqor=verified.max_fee_uqor,
    )
    return verified, evaluate(policy, state, request)
