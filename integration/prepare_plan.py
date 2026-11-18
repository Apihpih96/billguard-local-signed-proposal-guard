#!/usr/bin/env python3
"""Create a non-executable, owner-reviewable BillGuard testnet plan template."""
from __future__ import annotations
import json


def build_plan() -> dict:
    return {
        "status": "draft_template_not_executable",
        "network": {
            "name": "qorechain-diana",
            "evm_chain_id": 9800,
            "evm_rpc": "https://evm-testnet.qore.host",
            "cosmos_rest": "https://api-testnet.qore.host",
        },
        "concept": "BillGuard: one owner-authorized, short-lived agent permission for one fixed QOR recipient.",
        "candidate_flow": [
            "Owner uses a QoreChain testnet account with an eth_secp256k1 EVM key and a registered ML-DSA-87 key.",
            "Owner explicitly authorizes a bounded EVM window; the EVM window-opening message is a hybrid-signed Cosmos-lane action.",
            "For autonomous execution, owner links an EVM authenticator with a short expiry and an enabled spending rule that has nonzero per-transaction and daily limits and allowed_denoms=['uqor'].",
            "Agent signs only the chain-bound authenticator digest; an authorized relayer would submit/pay for the outer hybrid-signed Cosmos transaction.",
            "Use one fixed recipient and a single test transfer; capture the owner-visible authorization, bounded rule and resulting testnet receipt before making any bounty claim.",
        ],
        "owner_review_fields": {
            "owner_qor1_account": None,
            "owner_evm_address": None,
            "agent_evm_address": None,
            "fixed_recipient_evm_address": None,
            "window_blocks": None,
            "window_max_txs": None,
            "window_max_value_uqor_including_max_fee": None,
            "authenticator_expiry_unix": None,
            "spending_rule_per_tx_uqor": None,
            "spending_rule_daily_uqor": None,
        },
        "safety": {
            "window_scope_candidate": "nativeOnly=true and allow only the fixed recipient when supported and consistent with the intended transfer; otherwise stop and reassess scope.",
            "no_generic_contract_router": True,
            "no_private_keys_or_recovery_codes_in_app": True,
            "no_secrets_requested_or_handled": True,
            "broadcast_or_registration_performed": False,
            "owner_signed_setup_required": True,
            "public_transaction_requires_separate_owner_approval": True,
        },
        "gaps": [
            "This repository currently remains a local simulation; this template is not chain integration.",
            "The event page requires a scoped EVM window, transaction/value/duration/target bounds, smart-account spending rules, and authenticated messaging; the organizer has not defined what 'authenticated messaging' must mean.",
            "The official wallet-adapter docs say its signing/QoreX snippets were not tested end-to-end; the proposed linking and execution flow must be verified with a controlled test account before claims.",
            "Wallet-adapter docs report no authenticator nonce query yet, while the current Rust SDK docs expose fetch_auth_nonce for testnet v3.2.4+; verify the exact supported client path before implementing.",
            "An EVM window caps native QOR value plus maximum fee, not arbitrary token amounts; linked spending rules are separately needed for authorized account executions.",
        ],
    }


def main() -> None:
    print(json.dumps(build_plan(), indent=2))


if __name__ == "__main__":
    main()
