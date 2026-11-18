"""Local explanatory simulator for QoreChain v3.2.8 EVM window rules.

This is not chain code and does not prove or enforce QoreChain account state.
"""
from dataclasses import dataclass, field

MAX_BLOCKS = 17_280
MAX_TXS = 1_000
MAX_TARGETS = 16
WEI_PER_UQOR = 10**12  # 1 QOR = 10^18 wei = 10^6 uqor.


def _uint(value: object, name: str, *, positive: bool = False) -> int:
    """Require a real Python integer, not bools or fractional numbers."""
    if type(value) is not int or value < (1 if positive else 0):
        qualifier = "positive " if positive else "nonnegative "
        raise ValueError(f"{name} must be a {qualifier}integer")
    return value


def max_value_charge_uqor(tx_value_wei: int, gas_limit: int, fee_cap_wei: int) -> int:
    """Documented ante charge: value + gas_limit*fee_cap, converted to uqor, ceil."""
    tx_value_wei = _uint(tx_value_wei, "tx_value_wei")
    gas_limit = _uint(gas_limit, "gas_limit", positive=True)
    fee_cap_wei = _uint(fee_cap_wei, "fee_cap_wei")
    wei = tx_value_wei + gas_limit * fee_cap_wei
    return (wei + WEI_PER_UQOR - 1) // WEI_PER_UQOR


def _validate_target(address: str) -> str:
    if (not isinstance(address, str) or len(address) != 42
            or not address.startswith("0x")
            or any(char not in "0123456789abcdefABCDEF" for char in address[2:])):
        raise ValueError("target must be a 20-byte ASCII hexadecimal 0x address")
    return address.lower()


@dataclass
class EvmWindowModel:
    opened_at: int
    blocks: int
    max_txs: int
    max_value_uqor: int
    native_only: bool = False
    allowed_targets: tuple[str, ...] = ()
    used_txs: int = 0
    used_value_uqor: int = 0
    charges: list[int] = field(default_factory=list)

    def __post_init__(self):
        _uint(self.opened_at, "opened_at")
        _uint(self.blocks, "blocks", positive=True)
        _uint(self.max_txs, "max_txs", positive=True)
        _uint(self.max_value_uqor, "max_value_uqor", positive=True)
        _uint(self.used_txs, "used_txs")
        _uint(self.used_value_uqor, "used_value_uqor")
        if self.used_txs > self.max_txs or self.used_value_uqor > self.max_value_uqor:
            raise ValueError("initial usage exceeds the configured window")
        if not isinstance(self.native_only, bool):
            raise ValueError("native_only must be a boolean")
        if not isinstance(self.allowed_targets, (tuple, list)):
            raise ValueError("allowed_targets must be a sequence of addresses")
        if not isinstance(self.charges, list) or any(type(charge) is not int or charge < 0 for charge in self.charges):
            raise ValueError("charges must be a list of nonnegative integers")
        if not 1 <= self.blocks <= MAX_BLOCKS:
            raise ValueError("blocks must be 1..17,280")
        if not 1 <= self.max_txs <= MAX_TXS:
            raise ValueError("max_txs must be 1..1,000")
        if len(self.allowed_targets) > MAX_TARGETS:
            raise ValueError("allowed_targets allows at most 16 addresses")
        normalized = tuple(_validate_target(x) for x in self.allowed_targets)
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed_targets must not contain duplicates")
        self.allowed_targets = normalized

    @property
    def expires_at_height(self) -> int:
        return self.opened_at + self.blocks

    def admits(self, *, height: int, to: str | None, value_wei: int,
               gas_limit: int, fee_cap_wei: int, calldata: bytes = b"",
               creates_contract: bool = False, recipient_has_code: bool = False,
               eip7702_authorization: bool = False, reverted_after_admission: bool = False) -> int:
        """Validate and charge one admitted EVM transaction; returns uqor charge.

        The charge is made at admission. Even if the EVM execution subsequently reverts,
        documented QoreChain behavior still consumes its transaction slot and value budget.
        """
        height = _uint(height, "height")
        charge = max_value_charge_uqor(value_wei, gas_limit, fee_cap_wei)
        for name, flag in (("creates_contract", creates_contract),
                           ("recipient_has_code", recipient_has_code),
                           ("eip7702_authorization", eip7702_authorization),
                           ("reverted_after_admission", reverted_after_admission)):
            if not isinstance(flag, bool):
                raise ValueError(f"{name} must be a boolean")
        if not isinstance(calldata, bytes):
            raise ValueError("calldata must be bytes")
        if not self.opened_at <= height <= self.expires_at_height:
            raise ValueError("outside block window")
        if self.used_txs >= self.max_txs:
            raise ValueError("transaction count exhausted")
        if creates_contract:
            if self.native_only or self.allowed_targets:
                raise ValueError("scoped/native_only window refuses contract creation")
        else:
            if to is None:
                raise ValueError("recipient required")
            target = _validate_target(to)
            if self.allowed_targets and target not in self.allowed_targets:
                raise ValueError("recipient not allowlisted")
            if self.native_only and (calldata or recipient_has_code or eip7702_authorization):
                raise ValueError("native_only permits plain QOR transfer only")
        if self.used_value_uqor + charge > self.max_value_uqor:
            raise ValueError("max_value exhausted")
        self.used_txs += 1
        self.used_value_uqor += charge
        self.charges.append(charge)
        # A reverted admitted transaction is still charged; the outcome does not alter accounting.
        return charge

    def native_lane_action(self, *_args, **_kwargs) -> None:
        """Native-lane actions are outside EVM-window accounting."""
        return None

    def abstract_account_execution(self, *_args, **_kwargs) -> None:
        """Abstract-account executions authorized by authenticators are outside this window."""
        return None
