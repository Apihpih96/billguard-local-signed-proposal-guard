#!/usr/bin/env python3
"""Run a deterministic fixture through the local capped-payment validator."""
from __future__ import annotations

import json
from capped_payment import build_capped_plan


# Clearly synthetic addresses/amounts: this is not the owner's account or a live offer.
PAYMENT = {
    "sender": "0x1111111111111111111111111111111111111111",
    "recipient": "0x2222222222222222222222222222222222222222",
    "amount_uqor": 1_000_000,
    "max_fee_uqor": 100_000,
    "denom": "uqor",
    "calldata": "0x",
}
WINDOW = {
    "blocks": 300,
    "max_txs": 1,
    "max_value_uqor": 1_100_000,
    "allowed_targets": [PAYMENT["recipient"]],
    "native_only": True,
}
SPENDING_RULE = {
    "enabled": True,
    "per_tx_uqor": 1_100_000,
    "daily_uqor": 2_000_000,
    "allowed_denoms": ["uqor"],
}


def main() -> None:
    print(json.dumps(build_capped_plan(PAYMENT, WINDOW, SPENDING_RULE), indent=2))


if __name__ == "__main__":
    main()
