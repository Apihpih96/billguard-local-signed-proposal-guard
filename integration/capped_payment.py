#!/usr/bin/env python3
"""Build an offline, review-only capped native-QOR payment plan.

This module has no network, wallet, signing, or broadcast code. It validates
that one proposed native transfer fits distinct EVM-window and abstract-account
spending caps, then returns a displayable draft only.
"""
from __future__ import annotations

import re
from typing import Any

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _address(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ADDRESS.fullmatch(value):
        raise ValueError(f"{field} must be a 20-byte EVM address")
    return value.lower()


def build_capped_plan(payment: dict, window: dict, spending_rule: dict) -> dict:
    """Return a non-executable plan when all independent caps admit the transfer."""
    if not isinstance(payment, dict):
        raise ValueError("payment must be an object")
    if not isinstance(window, dict):
        raise ValueError("window must be an object")
    if not isinstance(spending_rule, dict):
        raise ValueError("spending_rule must be an object")
    if set(payment) != {"sender", "recipient", "amount_uqor", "max_fee_uqor", "denom", "calldata"}:
        raise ValueError("payment must contain exactly the documented fields")
    sender = _address(payment["sender"], "sender")
    recipient = _address(payment["recipient"], "recipient")
    amount = _positive_int(payment["amount_uqor"], "amount_uqor")
    fee = _positive_int(payment["max_fee_uqor"], "max_fee_uqor")
    if payment["denom"] != "uqor":
        raise ValueError("only native uqor transfers are supported")
    if payment["calldata"] not in (None, "", "0x"):
        raise ValueError("native-only demo refuses calldata")

    if set(window) != {"blocks", "max_txs", "max_value_uqor", "allowed_targets", "native_only"}:
        raise ValueError("window must contain exactly the documented fields")
    blocks = _positive_int(window["blocks"], "window.blocks")
    max_txs = _positive_int(window["max_txs"], "window.max_txs")
    max_value = _positive_int(window["max_value_uqor"], "window.max_value_uqor")
    if not 1 <= blocks <= 17_280:
        raise ValueError("window.blocks must be within the documented 1..17280 range")
    if not 1 <= max_txs <= 1_000:
        raise ValueError("window.max_txs must be within the documented 1..1000 range")
    if max_txs != 1:
        raise ValueError("BillGuard demo requires a one-transaction window")
    if window["native_only"] is not True:
        raise ValueError("BillGuard demo requires native_only=true")
    targets = window["allowed_targets"]
    if not isinstance(targets, list) or len(targets) != 1:
        raise ValueError("BillGuard demo requires exactly one allowed target")
    allowed_target = _address(targets[0], "window.allowed_targets[0]")
    if recipient != allowed_target:
        raise ValueError("payment recipient does not match the sole allowed target")
    total = amount + fee
    if total > max_value:
        raise ValueError("transfer amount plus maximum fee exceeds EVM window cap")

    required_rule = {"enabled", "per_tx_uqor", "daily_uqor", "allowed_denoms"}
    if set(spending_rule) != required_rule:
        raise ValueError("spending_rule must contain exactly the documented fields")
    if spending_rule["enabled"] is not True:
        raise ValueError("abstract-account spending rule must be enabled")
    per_tx = _positive_int(spending_rule["per_tx_uqor"], "spending_rule.per_tx_uqor")
    daily = _positive_int(spending_rule["daily_uqor"], "spending_rule.daily_uqor")
    denoms = spending_rule["allowed_denoms"]
    if denoms != ["uqor"]:
        raise ValueError("spending rule must allow only the native uqor denomination")
    if total > per_tx:
        raise ValueError("transfer amount plus maximum fee exceeds per-transaction cap")
    if total > daily:
        raise ValueError("transfer amount plus maximum fee exceeds daily cap")

    return {
        "status": "local_plan_passes_simulated_caps",
        "network": {"name": "qorechain-diana", "evm_chain_id": 9800},
        "payment": {
            "sender": sender,
            "recipient": recipient,
            "denom": "uqor",
            "amount_uqor": amount,
            "max_fee_uqor": fee,
            "worst_case_outflow_uqor": total,
            "calldata": "0x",
        },
        "evm_window": {
            "blocks": blocks,
            "max_txs": max_txs,
            "max_value_uqor": max_value,
            "allowed_targets": [allowed_target],
            "native_only": True,
        },
        "abstract_account_spending_rule": {
            "enabled": True,
            "per_tx_uqor": per_tx,
            "daily_uqor": daily,
            "allowed_denoms": ["uqor"],
        },
        "checks": {
            "single_native_transfer": True,
            "fixed_recipient_allowlist_match": True,
            "amount_plus_max_fee_within_evm_window": True,
            "amount_plus_max_fee_within_per_tx_rule": True,
            "amount_plus_max_fee_within_daily_rule": True,
            "owner_exact_review_required_before_any_live_transaction": True,
        },
        "execution": {
            "signing_performed": False,
            "authorization_window_opened": False,
            "broadcast_performed": False,
            "chain_state_changed": False,
            "executable": False,
        },
        "limitations": [
            "This is local arithmetic and input validation, not QoreChain enforcement.",
            "The abstract-account rule and EVM window are separate controls; this output proves neither exists on-chain.",
            "Every live transaction and any owner-signed setup requires separate exact review.",
        ],
    }
