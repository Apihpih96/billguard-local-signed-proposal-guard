"""BillGuard local policy simulator; not a QoreChain client or signer."""
from dataclasses import dataclass, field

@dataclass
class Policy:
    start_block: int
    block_limit: int
    tx_limit: int
    value_limit_uqor: int
    allowed_targets: set[str]

@dataclass
class Request:
    sender_authenticated: bool
    nonce: int | str
    current_block: int
    target: str
    value_uqor: int
    max_fee_uqor: int

@dataclass
class State:
    used_txs: int = 0
    reserved_uqor: int = 0
    seen_nonces: set[int | str] = field(default_factory=set)

@dataclass
class Decision:
    allowed: bool
    reason: str
    used_txs: int
    reserved_uqor: int


def _is_int(value: object) -> bool:
    """Python bools are ints, but policy arithmetic must use actual integer values."""
    return type(value) is int


def evaluate(policy: Policy, state: State, req: Request) -> Decision:
    """Apply a deterministic *simulated* admission policy.

    `max_fee_uqor` is a supplied fee ceiling for demo arithmetic. Real QoreChain
    window accounting uses gas_limit × max_fee_per_gas and actual tx value; this
    local model does not construct or validate an EVM transaction.
    """
    def deny(reason: str) -> Decision:
        return Decision(False, reason, state.used_txs, state.reserved_uqor)

    # Fail closed on malformed runtime input: in particular, the string "false"
    # must never be interpreted as an authenticated sender just because it is truthy.
    if req.sender_authenticated is not True:
        return deny("sender authentication not verified")
    if (not (_is_int(req.nonce) or isinstance(req.nonce, str))
            or isinstance(req.nonce, bool)):
        return deny("invalid request nonce")
    if not _is_int(req.current_block) or req.current_block < 0:
        return deny("invalid current block")
    if not isinstance(req.target, str):
        return deny("invalid target")
    if (not _is_int(req.value_uqor) or not _is_int(req.max_fee_uqor)
            or req.value_uqor < 0 or req.max_fee_uqor < 0):
        return deny("invalid value or fee")
    if (not _is_int(state.used_txs) or state.used_txs < 0
            or not _is_int(state.reserved_uqor) or state.reserved_uqor < 0
            or not isinstance(state.seen_nonces, set)):
        return deny("invalid simulator state")
    if (not _is_int(policy.start_block) or policy.start_block < 0
            or not _is_int(policy.block_limit) or policy.block_limit <= 0
            or not _is_int(policy.tx_limit) or policy.tx_limit <= 0
            or not _is_int(policy.value_limit_uqor) or policy.value_limit_uqor < 0
            or not isinstance(policy.allowed_targets, set)
            or not all(isinstance(target, str) for target in policy.allowed_targets)):
        return deny("invalid policy")
    if req.nonce in state.seen_nonces:
        return deny("replayed request nonce")
    if not (policy.start_block <= req.current_block < policy.start_block + policy.block_limit):
        return deny("outside the block window")
    if req.target.lower() not in {t.lower() for t in policy.allowed_targets}:
        return deny("target is not allowlisted")
    if state.used_txs >= policy.tx_limit:
        return deny("transaction limit exhausted")
    reserve = req.value_uqor + req.max_fee_uqor
    if state.reserved_uqor + reserve > policy.value_limit_uqor:
        return deny("value plus fee ceiling exceeds the budget")
    # An admitted slot and reserve are consumed even if eventual chain execution fails.
    state.used_txs += 1
    state.reserved_uqor += reserve
    state.seen_nonces.add(req.nonce)
    return Decision(True, "within simulated limits", state.used_txs, state.reserved_uqor)
