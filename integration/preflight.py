#!/usr/bin/env python3
"""Read-only QoreChain Diana environment preflight; never signs or submits."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api-testnet.qore.host"
PATHS = {
    "abstract_account_config": "/qorechain/abstractaccount/v1/config",
    "permission_schema": "/qorechain/abstractaccount/v1/permission_schema",
    "evm_limits": "/qorechain/pqc/v1/evm_limits",
}


def assess(config: dict, schema: dict, evm_limits: dict) -> dict:
    """Assess environment-wide prerequisites only; does not prove account readiness."""
    config = config if isinstance(config, dict) else {}
    schema = schema if isinstance(schema, dict) else {}
    evm_limits = evm_limits if isinstance(evm_limits, dict) else {}
    raw_cfg = config.get("config", config)
    cfg = raw_cfg if isinstance(raw_cfg, dict) else {}
    raw_limits = evm_limits.get("limits", {})
    limits = raw_limits if isinstance(raw_limits, dict) else {}
    # Prefer the documented top-level field when present; do not silently mask a
    # malformed/zero value with a different nested field.
    max_gas = evm_limits["tx_max_gas"] if "tx_max_gas" in evm_limits else limits.get("tx_max_gas")
    permissions = schema.get("permissions", [])
    valid_permissions = isinstance(permissions, list) and all(
        isinstance(permission, str) for permission in permissions
    )
    checks = {
        "abstract_account_enabled": cfg.get("enabled") is True,
        "evm_permission_present": valid_permissions and "evm" in permissions,
        "positive_testnet_evm_gas_limit": _positive_int(max_gas),
    }
    return {
        "checks": checks,
        "environment_ready_for_account_specific_review": all(checks.values()),
        "account_specific_readiness_checked": False,
        "notes": [
            "This checks public, environment-wide REST data only.",
            "It does not prove an account has a registered ML-DSA key, linked authenticator, funded balance, active spending rule, or open EVM window.",
            "It does not sign, broadcast, register, open a window, or change chain state.",
        ],
    }


def _positive_int(value) -> bool:
    # JSON responses may encode documented integer fields as decimal strings,
    # but booleans, floats (including 1.5), and coercible objects are not proof.
    if type(value) is int:
        return value > 0
    if isinstance(value, str) and value.isascii() and value.isdigit():
        try:
            return int(value) > 0
        except ValueError:
            # Python limits decimal-to-int conversion length; malformed oversized
            # server values must fail closed rather than crash the preflight.
            return False
    return False


def get_json(path: str, timeout: int = 15) -> dict:
    req = Request(BASE + path, headers={"Accept": "application/json", "User-Agent": "BillGuard-ReadOnly-Preflight/1.0"})
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        try:
            text = response.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("REST response is not valid UTF-8") from exc
        try:
            payload = json.loads(text)
        except RecursionError as exc:
            raise RuntimeError("REST response JSON is nested too deeply") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("REST response must be a JSON object")
        return payload


def main() -> int:
    result = {
        "network": "qorechain-diana",
        "chain_id": 9800,
        "rest_endpoint": BASE,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_reads_only": True,
    }
    payloads, errors = {}, {}
    for key, path in PATHS.items():
        try:
            payloads[key] = get_json(path)
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"
    if errors:
        result["fetch_errors"] = errors
        result["environment_ready_for_account_specific_review"] = False
        result["account_specific_readiness_checked"] = False
        result["note"] = "A failed REST read is inconclusive; no chain write was attempted."
        print(json.dumps(result, indent=2))
        return 2
    config_data = payloads["abstract_account_config"]
    raw_config = config_data.get("config", config_data)
    observed_config = raw_config if isinstance(raw_config, dict) else {}
    schema_data = payloads["permission_schema"]
    raw_permissions = schema_data.get("permissions", [])
    permissions = raw_permissions if isinstance(raw_permissions, list) else []
    limits_data = payloads["evm_limits"]
    nested_limits = limits_data.get("limits", {})
    nested_limits = nested_limits if isinstance(nested_limits, dict) else {}
    result.update(assess(config_data, schema_data, limits_data))
    result["observed"] = {
        "abstract_account_enabled": observed_config.get("enabled"),
        "max_spending_rules": observed_config.get("max_spending_rules"),
        "evm_permission_present": "evm" in permissions,
        "testnet_tx_max_gas": limits_data.get("tx_max_gas", nested_limits.get("tx_max_gas")),
        "precompile_input_max_bytes": limits_data.get("precompile_input_max_bytes"),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["environment_ready_for_account_specific_review"] else 1


if __name__ == "__main__":
    sys.exit(main())
