import pytest
from window_model import EvmWindowModel, MAX_BLOCKS, MAX_TXS, WEI_PER_UQOR, max_value_charge_uqor

A = "0x1111111111111111111111111111111111111111"
B = "0x2222222222222222222222222222222222222222"


def window(**overrides):
    fields = dict(opened_at=100, blocks=5, max_txs=2, max_value_uqor=100_000,
                  native_only=False, allowed_targets=())
    fields.update(overrides)
    return EvmWindowModel(**fields)


def test_documented_block_and_transaction_bounds():
    assert window(blocks=1, max_txs=1).blocks == 1
    assert window(blocks=MAX_BLOCKS, max_txs=MAX_TXS).max_txs == 1000
    for blocks in (0, MAX_BLOCKS + 1):
        with pytest.raises(ValueError):
            window(blocks=blocks)
    for count in (0, MAX_TXS + 1):
        with pytest.raises(ValueError):
            window(max_txs=count)


def test_window_block_count_boundary():
    w = window(blocks=2)
    w.admits(height=102, to=A, value_wei=0, gas_limit=1, fee_cap_wei=0)
    with pytest.raises(ValueError, match="outside block window"):
        w.admits(height=103, to=A, value_wei=0, gas_limit=1, fee_cap_wei=0)


def test_value_is_native_value_plus_gas_limit_times_fee_cap_ceil_to_uqor():
    # 2 QOR transfer + (30m gas * 100 gwei) = 5 QOR = 5m uqor.
    assert max_value_charge_uqor(2 * 10**18, 30_000_000, 100 * 10**9) == 5_000_000
    # A fractional uqor rounds up, not down.
    assert max_value_charge_uqor(1, 1, 0) == 1
    w = window(max_value_uqor=5_000_000, max_txs=1)
    assert w.admits(height=101, to=A, value_wei=2 * 10**18,
                    gas_limit=30_000_000, fee_cap_wei=100 * 10**9) == 5_000_000


def test_value_cap_rejects_when_fee_reserve_pushes_over_limit():
    w = window(max_value_uqor=4_999_999, max_txs=1)
    with pytest.raises(ValueError, match="max_value"):
        w.admits(height=101, to=A, value_wei=2 * 10**18,
                  gas_limit=30_000_000, fee_cap_wei=100 * 10**9)


def test_admitted_reverted_tx_still_consumes_count_and_value():
    w = window(max_txs=1, max_value_uqor=100)
    w.admits(height=101, to=A, value_wei=7 * WEI_PER_UQOR,
             gas_limit=1, fee_cap_wei=0, reverted_after_admission=True)
    assert w.used_txs == 1
    assert w.used_value_uqor == 7
    with pytest.raises(ValueError, match="transaction count"):
        w.admits(height=101, to=A, value_wei=0, gas_limit=1, fee_cap_wei=0)


def test_target_allowlist_and_limit():
    w = window(allowed_targets=(A,))
    w.admits(height=101, to=A, value_wei=0, gas_limit=1, fee_cap_wei=0)
    with pytest.raises(ValueError, match="allowlisted"):
        window(allowed_targets=(A,)).admits(height=101, to=B, value_wei=0,
                                            gas_limit=1, fee_cap_wei=0)
    with pytest.raises(ValueError, match="at most 16"):
        window(allowed_targets=tuple(f"0x{i:040x}" for i in range(17)))
    with pytest.raises(ValueError, match="duplicates"):
        window(allowed_targets=(A, A))


def test_allowlisted_contract_call_does_not_cap_token_amount():
    # The window gates the contract recipient; EVM value is zero for a token-call payload.
    w = window(allowed_targets=(A,), max_value_uqor=1)
    assert w.admits(height=101, to=A, value_wei=0, gas_limit=1,
                    fee_cap_wei=WEI_PER_UQOR, calldata=b"transfer(huge token amount)") == 1
    assert w.used_value_uqor == 1


def test_native_only_accepts_plain_native_transfer_only():
    w = window(native_only=True)
    w.admits(height=101, to=A, value_wei=1, gas_limit=1, fee_cap_wei=0)
    for kwargs in (
        {"calldata": b"call"},
        {"recipient_has_code": True},
        {"eip7702_authorization": True},
    ):
        with pytest.raises(ValueError, match="native_only"):
            window(native_only=True).admits(height=101, to=A, value_wei=1,
                                           gas_limit=1, fee_cap_wei=0, **kwargs)
    with pytest.raises(ValueError, match="contract creation"):
        window(native_only=True).admits(height=101, to=None, value_wei=0,
                                        gas_limit=1, fee_cap_wei=0, creates_contract=True)


def test_scoped_window_refuses_contract_creation():
    with pytest.raises(ValueError, match="contract creation"):
        window(allowed_targets=(A,)).admits(height=101, to=None, value_wei=0,
                                           gas_limit=1, fee_cap_wei=0, creates_contract=True)


def test_cosmos_native_and_abstract_account_actions_do_not_consume_evm_window():
    w = window()
    w.native_lane_action("bank-send")
    w.abstract_account_execution("authenticator-authorized")
    assert (w.used_txs, w.used_value_uqor) == (0, 0)


def test_basic_invalid_bounds_and_values():
    for kwargs in ({"max_value_uqor": 0},):
        with pytest.raises(ValueError):
            window(**kwargs)
    with pytest.raises(ValueError, match="negative"):
        max_value_charge_uqor(-1, 1, 1)


def test_rejects_boolean_and_fractional_numeric_inputs():
    for kwargs in (
        {"opened_at": 100.5},
        {"blocks": True},
        {"max_txs": 1.5},
        {"max_value_uqor": 1.5},
    ):
        fields = dict(opened_at=100, blocks=5, max_txs=2, max_value_uqor=100)
        fields.update(kwargs)
        with pytest.raises(ValueError):
            EvmWindowModel(**fields)
    for args in ((1.5, 1, 0), (True, 1, 0), (0, 0, 0.5), (0, 0, 0)):
        with pytest.raises(ValueError):
            max_value_charge_uqor(*args)
    w = window(max_txs=1)
    with pytest.raises(ValueError):
        w.admits(height=101.5, to=A, value_wei=0, gas_limit=1, fee_cap_wei=0)
    assert (w.used_txs, w.used_value_uqor) == (0, 0)


def test_rejects_nonboolean_policy_flags_and_nonbyte_calldata():
    with pytest.raises(ValueError, match="native_only"):
        window(native_only="false")
    with pytest.raises(ValueError, match="calldata"):
        window(native_only=True).admits(height=101, to=A, value_wei=0,
                                        gas_limit=1, fee_cap_wei=0, calldata="")


def test_address_parser_rejects_unicode_digits():
    for bad in ("0x" + "０" * 40, "0x" + "١" * 40):
        with pytest.raises(ValueError, match="ASCII hexadecimal"):
            window(allowed_targets=(bad,))
        with pytest.raises(ValueError, match="ASCII hexadecimal"):
            window().admits(height=101, to=bad, value_wei=0,
                            gas_limit=1, fee_cap_wei=0)


def test_gas_limit_must_be_positive_for_transaction_charge():
    with pytest.raises(ValueError, match="gas_limit must be a positive integer"):
        max_value_charge_uqor(0, 0, 0)
    with pytest.raises(ValueError, match="gas_limit must be a positive integer"):
        window().admits(height=101, to=A, value_wei=0,
                        gas_limit=0, fee_cap_wei=0)
