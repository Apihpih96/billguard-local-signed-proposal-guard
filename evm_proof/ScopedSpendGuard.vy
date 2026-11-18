# Local EVM proof-of-concept only. This is NOT QoreChain's native
# MsgOpenEVMWindow / abstract-account authorization implementation.
# A configured agent may call one fixed native-value recipient within limits.

# pragma version 0.4.3

agent: public(address)
recipient: public(address)
max_tx_count: public(uint256)
max_per_tx: public(uint256)
max_total: public(uint256)
expires_at_block: public(uint256)
call_count: public(uint256)
spent: public(uint256)


@deploy
@payable
def __init__(
    _agent: address,
    _recipient: address,
    _max_tx_count: uint256,
    _max_per_tx: uint256,
    _max_total: uint256,
    _duration_blocks: uint256,
):
    assert _agent != empty(address), "zero agent"
    assert _recipient != empty(address), "zero recipient"
    assert _max_tx_count > 0, "zero tx cap"
    assert _max_per_tx > 0, "zero per-tx cap"
    assert _max_total >= _max_per_tx, "total below per-tx"
    assert _duration_blocks > 0, "zero duration"
    self.agent = _agent
    self.recipient = _recipient
    self.max_tx_count = _max_tx_count
    self.max_per_tx = _max_per_tx
    self.max_total = _max_total
    self.expires_at_block = block.number + _duration_blocks


@external
@payable
def execute(_value: uint256):
    assert msg.sender == self.agent, "agent only"
    assert block.number <= self.expires_at_block, "window expired"
    assert self.call_count < self.max_tx_count, "tx cap"
    assert _value > 0, "zero value"
    assert _value <= self.max_per_tx, "per-tx cap"
    assert self.spent + _value <= self.max_total, "total cap"

    self.call_count += 1
    self.spent += _value
    raw_call(self.recipient, b"", value=_value, revert_on_failure=True)
