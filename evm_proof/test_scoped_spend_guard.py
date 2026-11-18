import pytest
from eth_tester import EthereumTester, PyEVMBackend
from web3 import EthereumTesterProvider, Web3
from vyper import compile_code

with open("evm_proof/ScopedSpendGuard.vy", encoding="utf-8") as source:
    CONTRACT = source.read()
COMPILED = compile_code(CONTRACT, output_formats=["abi", "bytecode"])


@pytest.fixture
def deployed():
    w3 = Web3(EthereumTesterProvider(EthereumTester(PyEVMBackend())))
    deployer, agent, recipient, other = w3.eth.accounts[:4]
    factory = w3.eth.contract(abi=COMPILED["abi"], bytecode=COMPILED["bytecode"])
    receipt = w3.eth.wait_for_transaction_receipt(
        factory.constructor(agent, recipient, 2, Web3.to_wei(3, "ether"), Web3.to_wei(5, "ether"), 8).transact({"from": deployer, "value": Web3.to_wei(10, "ether")})
    )
    guard = w3.eth.contract(address=receipt.contractAddress, abi=COMPILED["abi"])
    return w3, guard, deployer, agent, recipient, other


def test_allowed_transfer_and_counters(deployed):
    w3, guard, _, agent, recipient, _ = deployed
    before = w3.eth.get_balance(recipient)
    receipt = w3.eth.wait_for_transaction_receipt(
        guard.functions.execute(Web3.to_wei(2, "ether")).transact({"from": agent})
    )
    assert receipt.status == 1
    assert w3.eth.get_balance(recipient) - before == Web3.to_wei(2, "ether")
    assert guard.functions.call_count().call() == 1
    assert guard.functions.spent().call() == Web3.to_wei(2, "ether")


def test_only_agent_can_call(deployed):
    _, guard, _, _, _, other = deployed
    with pytest.raises(Exception):
        guard.functions.execute(1).transact({"from": other})


def test_unlisted_target_is_impossible(deployed):
    w3, guard, _, agent, recipient, other = deployed
    other_before = w3.eth.get_balance(other)
    recipient_before = w3.eth.get_balance(recipient)
    guard.functions.execute(1).transact({"from": agent})
    assert w3.eth.get_balance(other) == other_before
    assert w3.eth.get_balance(recipient) == recipient_before + 1


def test_per_transaction_value_cap(deployed):
    _, guard, _, agent, _, _ = deployed
    with pytest.raises(Exception):
        guard.functions.execute(Web3.to_wei(4, "ether")).transact({"from": agent})


def test_cumulative_value_cap(deployed):
    _, guard, _, agent, _, _ = deployed
    guard.functions.execute(Web3.to_wei(3, "ether")).transact({"from": agent})
    with pytest.raises(Exception):
        guard.functions.execute(Web3.to_wei(3, "ether")).transact({"from": agent})
    assert guard.functions.call_count().call() == 1
    assert guard.functions.spent().call() == Web3.to_wei(3, "ether")


def test_successful_call_count_cap(deployed):
    _, guard, _, agent, _, _ = deployed
    guard.functions.execute(1).transact({"from": agent})
    guard.functions.execute(1).transact({"from": agent})
    with pytest.raises(Exception):
        guard.functions.execute(1).transact({"from": agent})
    assert guard.functions.call_count().call() == 2


def test_block_height_expiry(deployed):
    w3, guard, _, agent, _, _ = deployed
    expiry = guard.functions.expires_at_block().call()
    now = w3.eth.block_number
    if expiry > now:
        w3.provider.ethereum_tester.mine_blocks(expiry - now - 1)
    assert w3.eth.block_number == expiry - 1
    receipt = w3.eth.wait_for_transaction_receipt(guard.functions.execute(1).transact({"from": agent}))
    assert receipt.blockNumber == expiry
    w3.provider.ethereum_tester.mine_blocks(1)
    with pytest.raises(Exception):
        guard.functions.execute(1).transact({"from": agent})


def test_zero_value_rejected(deployed):
    _, guard, _, agent, _, _ = deployed
    with pytest.raises(Exception):
        guard.functions.execute(0).transact({"from": agent})
