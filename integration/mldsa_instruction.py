"""Isolated FIPS 204 ML-DSA-87 signed-instruction harness for local BillGuard tests.

Uses pqcrypto's standard ML-DSA-87 implementation with a freshly generated
throwaway keypair. This authenticates a canonical local JSON instruction; it is
NOT QoreChain's address-bound key derivation, Cosmos hybrid-signature envelope,
wallet-adapter flow, or on-chain EVM authorization.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import MutableSet
from dataclasses import dataclass

from pqcrypto import InvalidSignatureError
from pqcrypto.sign import ml_dsa_87

PAYLOAD_FIELDS = {
    "version", "domain", "chain_id", "sender", "nonce", "issued_at", "expires_at",
    "action", "recipient", "value_uqor", "max_fee_uqor",
}
ENVELOPE_FIELDS = {"payload", "public_key_hex", "signature_hex"}
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
MAX_U256 = (1 << 256) - 1


class MldsaInstructionError(ValueError):
    """A local instruction failed signature, context or replay checks."""


@dataclass(frozen=True)
class VerifiedMldsaInstruction:
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


def generate_throwaway_keypair() -> tuple[bytes, bytes]:
    """Generate (public_key, secret_key) using the FIPS 204 ML-DSA-87 primitive."""
    public_key, secret_key = ml_dsa_87.keygen()
    return public_key, secret_key


def sender_id(public_key: bytes) -> str:
    if len(public_key) != ml_dsa_87.PUBLIC_KEY_SIZE:
        raise MldsaInstructionError("wrong ML-DSA-87 public-key length")
    return "mldsa87:" + hashlib.sha256(public_key).hexdigest()


def canonical_payload(payload: dict) -> bytes:
    """Deterministic ASCII JSON representation of the signed, exact-field payload."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def sign_instruction(public_key: bytes, secret_key: bytes, *, domain: str, chain_id: int,
                      nonce: str, issued_at: int, expires_at: int, recipient: str,
                      value_uqor: int, max_fee_uqor: int) -> dict:
    """Sign a local BillGuard instruction. Caller must keep the key throwaway/local."""
    if len(public_key) != ml_dsa_87.PUBLIC_KEY_SIZE or len(secret_key) != ml_dsa_87.SECRET_KEY_SIZE:
        raise MldsaInstructionError("wrong ML-DSA-87 key length")
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
    signature = ml_dsa_87.sign(secret_key, canonical_payload(payload))
    return {"payload": payload, "public_key_hex": public_key.hex(),
            "signature_hex": signature.hex()}


def verify_instruction(envelope: dict, *, expected_sender: str, expected_domain: str,
                       expected_chain_id: int, now: int, seen_nonces: MutableSet[str],
                       max_ttl_seconds: int = 900, clock_skew_seconds: int = 30) -> VerifiedMldsaInstruction:
    """Verify ML-DSA-87 and enforce signed context, freshness and replay checks.

    Nonce storage belongs to the caller and is in-memory in this harness. A real
    service needs durable atomic replay prevention and chain/account state checks.
    """
    if not isinstance(expected_sender, str) or not isinstance(expected_domain, str):
        raise MldsaInstructionError("invalid verifier identity context")
    if type(expected_chain_id) is not int or type(now) is not int:
        raise MldsaInstructionError("chain id and current time must be integers")
    if (type(max_ttl_seconds) is not int or max_ttl_seconds <= 0
            or type(clock_skew_seconds) is not int or clock_skew_seconds < 0):
        raise MldsaInstructionError("invalid verifier time policy")
    if not isinstance(seen_nonces, MutableSet):
        raise MldsaInstructionError("nonce store must be a mutable set")
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
        raise MldsaInstructionError("invalid envelope fields")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS:
        raise MldsaInstructionError("invalid instruction fields")
    pub_hex, sig_hex = envelope.get("public_key_hex"), envelope.get("signature_hex")
    if not isinstance(pub_hex, str) or not isinstance(sig_hex, str):
        raise MldsaInstructionError("invalid key or signature encoding")
    try:
        public_key, signature = bytes.fromhex(pub_hex), bytes.fromhex(sig_hex)
        if len(public_key) != ml_dsa_87.PUBLIC_KEY_SIZE:
            raise ValueError("wrong public key length")
        if len(signature) != ml_dsa_87.SIGNATURE_SIZE:
            raise ValueError("wrong signature length")
        ml_dsa_87.verify(public_key, canonical_payload(payload), signature)
    except (ValueError, InvalidSignatureError, TypeError, UnicodeError, RecursionError) as exc:
        raise MldsaInstructionError("ML-DSA-87 signature verification failed") from exc

    if type(payload["version"]) is not int or payload["version"] != 1:
        raise MldsaInstructionError("unsupported protocol version")
    if not isinstance(payload["domain"], str) or payload["domain"] != expected_domain:
        raise MldsaInstructionError("wrong application domain")
    if type(payload["chain_id"]) is not int or payload["chain_id"] != expected_chain_id:
        raise MldsaInstructionError("wrong chain")
    derived_sender = sender_id(public_key)
    if payload["sender"] != derived_sender or derived_sender != expected_sender:
        raise MldsaInstructionError("wrong sender")
    nonce = payload["nonce"]
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        raise MldsaInstructionError("invalid nonce")
    issued, expires = payload["issued_at"], payload["expires_at"]
    if type(issued) is not int or type(expires) is not int:
        raise MldsaInstructionError("invalid instruction times")
    if issued > now + clock_skew_seconds:
        raise MldsaInstructionError("instruction issued in the future")
    if expires <= now or expires <= issued:
        raise MldsaInstructionError("instruction expired or has invalid expiry")
    if expires - issued > max_ttl_seconds:
        raise MldsaInstructionError("instruction lifetime exceeds policy")
    if payload["action"] != "pay_qor":
        raise MldsaInstructionError("unsupported action")
    recipient = payload["recipient"]
    if not isinstance(recipient, str) or not ADDRESS_RE.fullmatch(recipient):
        raise MldsaInstructionError("invalid recipient")
    for field in ("value_uqor", "max_fee_uqor"):
        value = payload[field]
        if type(value) is not int or not 0 <= value <= MAX_U256:
            raise MldsaInstructionError(f"invalid {field}")
    replay_key = f"{derived_sender}:{nonce}"
    if replay_key in seen_nonces:
        raise MldsaInstructionError("replayed instruction nonce")
    seen_nonces.add(replay_key)
    return VerifiedMldsaInstruction(
        sender=derived_sender, domain=payload["domain"], chain_id=payload["chain_id"],
        nonce=nonce, issued_at=issued, expires_at=expires, action=payload["action"],
        recipient=recipient, value_uqor=payload["value_uqor"],
        max_fee_uqor=payload["max_fee_uqor"],
    )
