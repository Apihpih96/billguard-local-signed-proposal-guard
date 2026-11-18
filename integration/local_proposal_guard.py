#!/usr/bin/env python3
"""Local-only adapter from signed proposal JSON to BillGuard's existing guard.

Fixed values below are test fixtures, not observed account state or chain rules.
This script only returns a local plan/rejection; it cannot sign or broadcast.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integration.capped_payment import build_capped_plan

# Deliberately fixed local simulation values, not values supplied by the sender.
WINDOW = {
    "blocks": 120,
    "max_txs": 1,
    "max_value_uqor": 1_000_000,
    "allowed_targets": ["0x2222222222222222222222222222222222222222"],
    "native_only": True,
}
SPENDING_RULE = {
    "enabled": True,
    "per_tx_uqor": 800_000,
    "daily_uqor": 1_500_000,
    "allowed_denoms": ["uqor"],
}

def main() -> int:
    try:
        raw = sys.stdin.read(16_384)
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"payment"}:
            raise ValueError("request must contain only payment")
        plan = build_capped_plan(value["payment"], WINDOW, SPENDING_RULE)
        print(json.dumps({"accepted": True, "plan": plan}, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"accepted": False, "reason": str(exc)}, separators=(",", ":")))
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
