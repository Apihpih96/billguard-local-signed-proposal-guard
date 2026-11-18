#!/usr/bin/env python3
"""Read-only Diana account readiness inspector; never signs or submits transactions.

This tool only sends anonymous HTTPS GET requests to the public Diana REST host.
It accepts a public qor1 address, not secrets, and deliberately has no write path.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

BASE = "https://api-testnet.qore.host"
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 12
_QOR_RE = re.compile(r"^qor1[023456789acdefghjklmnpqrstuvwxyz]{20,}$")
ENV_PATHS = {
    "abstract_account_config": "/qorechain/abstractaccount/v1/config",
    "permission_schema": "/qorechain/abstractaccount/v1/permission_schema",
    "evm_limits": "/qorechain/pqc/v1/evm_limits",
}


def validate_account(account: str) -> None:
    """Reject path injection and obviously wrong network address forms."""
    if not _QOR_RE.fullmatch(account):
        raise ValueError("--account must be a lowercase qor1… Bech32 address")


def get_json(path: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Read one JSON object from the fixed public REST host, with size/time limits."""
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("REST path must be an absolute path on the configured host")
    url = BASE + path
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "BillGuard-Diana-ReadOnly/1.0"})
    with urlopen(request, timeout=timeout) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != urlsplit(BASE).hostname:
            raise RuntimeError("REST request redirected outside the configured HTTPS host")
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError("REST response exceeded the 1 MB safety limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RuntimeError(f"REST response is not a valid bounded JSON document: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("REST response must be a JSON object")
    return payload


def _as_bool(value):
    return value if type(value) is bool else None


def _list_of_dicts(value):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        return None
    return value


def _positive_decimal(value) -> bool:
    if type(value) is int:
        return value > 0
    if isinstance(value, str) and value.isascii() and value.isdigit():
        try:
            return int(value) > 0
        except ValueError:
            return False
    return False


def _rule_has_positive_uqor_caps(rule: dict) -> bool:
    """Recognize only an explicit enabled rule with positive uqor per-tx/day caps."""
    if _as_bool(rule.get("enabled")) is not True:
        return False
    denoms = rule.get("allowed_denoms")
    if not isinstance(denoms, list) or any(not isinstance(d, str) for d in denoms):
        return False
    if denoms and "uqor" not in denoms:
        return False
    limits = rule.get("denom_limits", [])
    if not isinstance(limits, list) or any(not isinstance(d, dict) for d in limits):
        return False
    uqor_limits = [d for d in limits if d.get("denom") == "uqor"]
    if uqor_limits:
        if len(uqor_limits) != 1:
            return False
        # A denom-specific limit replaces the base limit for that denom; do not
        # fall back to the base cap if the specific value is absent or zero.
        per = uqor_limits[0].get("per_tx_limit")
        daily = uqor_limits[0].get("daily_limit")
    else:
        per = rule.get("per_tx_limit")
        daily = rule.get("daily_limit")
    return _positive_decimal(per) and _positive_decimal(daily)


def _has_effective_rule(auth: dict, account_rules: list, key_rules: list) -> bool:
    own_rule_flag = _as_bool(auth.get("has_spend_rule"))
    if own_rule_flag is None:
        return False
    if own_rule_flag:
        pubkey = auth.get("pubkey_hex")
        if not isinstance(pubkey, str) or not pubkey:
            return False
        matches = [r for r in key_rules if r.get("pubkey_hex") == pubkey]
        return len(matches) == 1 and isinstance(matches[0].get("rule"), dict) and _rule_has_positive_uqor_caps(matches[0]["rule"])
    # The SDK documents the first enabled account-wide rule as the one that
    # bounds linked keys without a per-key rule. Do not skip an unsafe first one.
    first_enabled = next((r for r in account_rules if _as_bool(r.get("enabled")) is True), None)
    return isinstance(first_enabled, dict) and _rule_has_positive_uqor_caps(first_enabled)


def _exact_integer(value):
    """Preserve exact integer fields from REST string or JSON integer; reject float/bool."""
    if type(value) is int:
        return str(value)
    if isinstance(value, str) and value.strip():
        s = value.strip()
        if s.isascii() and (s.isdigit() or (s.startswith("-") and s[1:].isdigit())):
            return s
    return None


def summarize_account(account_data: dict, evm_data: dict, rules_data: dict, now_unix: int | None = None) -> dict:
    """Summarize only documented, strongly typed fields; unknown shapes stay unknown."""
    now_unix = int(time.time()) if now_unix is None else now_unix
    found = _as_bool(account_data.get("found"))
    key_status = "registered" if found is True else "not_registered" if found is False else "unknown"

    raw_auths = _list_of_dicts(evm_data.get("authenticators"))
    raw_rules = _list_of_dicts(rules_data.get("rules"))
    raw_key_rules = _list_of_dicts(rules_data.get("authenticator_rules"))
    account_rules = raw_rules or []
    key_rules = raw_key_rules or []

    active_evm_auth_count = None
    usable_auth_count = None
    if raw_auths is not None:
        live_auths = []
        for auth in raw_auths:
            expiry_text = _exact_integer(auth.get("expiry_unix"))
            permissions = auth.get("permissions")
            if (_as_bool(auth.get("revoked")) is False and expiry_text is not None
                    and int(expiry_text) > now_unix
                    and isinstance(permissions, list)
                    and all(isinstance(permission, str) for permission in permissions)
                    and "evm" in permissions):
                live_auths.append(auth)
        active_evm_auth_count = len(live_auths)
        usable_auth_count = sum(_has_effective_rule(auth, account_rules, key_rules) for auth in live_auths)

    window_found = _as_bool(evm_data.get("found"))
    window = None
    if window_found is True:
        window = {
            "live": _as_bool(evm_data.get("live")),
            "opened_height": _exact_integer(evm_data.get("opened_height")),
            "expiry_height": _exact_integer(evm_data.get("expiry_height")),
            "remaining_blocks": _exact_integer(evm_data.get("remaining_blocks")),
            "remaining_transactions": _exact_integer(evm_data.get("remaining_txs")),
            "remaining_value_uqor": _exact_integer(evm_data.get("remaining_value")),
            "max_value_uqor": _exact_integer(evm_data.get("max_value")),
            "native_only": _as_bool(evm_data.get("native_only")),
            "allowed_targets_count": len(evm_data["allowed_targets"])
                if isinstance(evm_data.get("allowed_targets"), list)
                and all(isinstance(x, str) for x in evm_data["allowed_targets"]) else None,
        }
    return {
        "pqc_key_status": key_status,
        "pqc_key_found_field": found,
        "evm_window_exists": window_found,
        "window": window,
        "active_evm_authenticator_count": active_evm_auth_count,
        "active_evm_authenticator_with_recognized_positive_uqor_rule_count": usable_auth_count,
        "account_wide_rule_count": len(account_rules) if raw_rules is not None else None,
        "per_authenticator_rule_count": len(key_rules) if raw_key_rules is not None else None,
        "notes": [
            "A window is counted live only when the chain's explicit live field is true; verify the recipient/scope before any test.",
            "EVM windows require the correct eth_secp256k1 identity; these REST reads do not verify key-type/address linkage.",
            "Rule recognition is deliberately narrow; unsupported or malformed response shapes remain unknown, not ready.",
        ],
    }


def inspect(fetcher=get_json, account: str = "", now_unix: int | None = None) -> dict:
    validate_account(account)
    account_path = quote(account, safe="")
    paths = dict(ENV_PATHS)
    paths.update({
        "pqc_key_status": "/qorechain/pqc/v1/account/" + account_path,
        "evm_window": "/qorechain/pqc/v1/evm_window/" + account_path,
        "authenticators": "/qorechain/abstractaccount/v1/accounts/" + account_path + "/authenticators",
        "spending_rules": "/qorechain/abstractaccount/v1/accounts/" + account_path + "/spending_rules",
    })
    results, errors = {}, {}
    for key, path in paths.items():
        try:
            payload = fetcher(path)
            if not isinstance(payload, dict):
                raise RuntimeError("response was not a JSON object")
            results[key] = payload
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"
    evm_data = dict(results.get("evm_window", {}))
    if "authenticators" in results:
        evm_data["authenticators"] = results["authenticators"].get("authenticators")
    rules_data = results.get("spending_rules", {})
    account_data = results.get("pqc_key_status", {})
    readiness = summarize_account(account_data, evm_data, rules_data, now_unix)

    if errors:
        return {
            "network": "qorechain-diana",
            "chain_id": 9800,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_get_only": True,
            "account_specific_readiness": readiness,
            "fetch_errors": errors,
            "readiness": "inconclusive",
            "no_chain_write_attempted": True,
        }

    try:
        from preflight import assess
        env = assess(results["abstract_account_config"], results["permission_schema"], results["evm_limits"])
        env_ready = env["environment_ready_for_account_specific_review"] is True
    except (ImportError, KeyError, TypeError):
        env_ready = False
    checks = [
        readiness["pqc_key_status"] == "registered",
        readiness["window"] is not None and readiness["window"]["live"] is True,
        readiness["active_evm_authenticator_with_recognized_positive_uqor_rule_count"] is not None
        and readiness["active_evm_authenticator_with_recognized_positive_uqor_rule_count"] > 0,
    ]
    return {
        "network": "qorechain-diana",
        "chain_id": 9800,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_get_only": True,
        "environment": {"documented_prerequisites_observed": env_ready},
        "account_specific_readiness": readiness,
        "readiness": "requires_manual_review" if env_ready and all(checks) else "not_ready_or_unknown",
        "warning": "This report does not validate account/EVM-address ownership linkage, signer key type, funds, target-specific effects, or complete bounty criteria.",
        "no_chain_write_attempted": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True, help="public qor1… abstract account address")
    args = parser.parse_args(argv)
    try:
        result = inspect(account=args.account)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result.get("readiness") == "requires_manual_review" else 2 if "fetch_errors" in result else 1


if __name__ == "__main__":
    sys.exit(main())
