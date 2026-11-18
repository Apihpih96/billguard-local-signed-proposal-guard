import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_GAS_LIMIT,
  NATIVE_DENOM,
  QORECHAIN_DIANA,
  formatQor,
  prepareNativePayment,
  requestOwnerReviewedPayment,
} from '../src/payment_core.mjs';

const sender = 'qor1' + 'a'.repeat(38);
const recipient = 'qor1' + 'c'.repeat(38);
const valid = () => prepareNativePayment({ fromAddress: sender, toAddress: recipient, amountUqor: '1250000' });

function stub(MsgSend) {
  const calls = [];
  return {
    calls,
    adapter: {
      hasQorexSignAndBroadcast: () => true,
      qorexSignAndBroadcast: async (value) => { calls.push(value); return { code: 0, txHash: 'ABC123' }; },
      isQorexRejection: () => false,
    },
    MsgSend,
  };
}

test('prepares exact Diana native transfer without signing or network access', () => {
  const request = valid();
  assert.equal(request.chainId, QORECHAIN_DIANA);
  assert.equal(request.amount[0].denom, NATIVE_DENOM);
  assert.equal(request.amount[0].amount, '1250000');
  assert.equal(request.ownerApprovalRequired, true);
  assert.equal(request.gasLimit, DEFAULT_GAS_LIMIT);
  assert.equal(formatQor('1250000'), '1.25 QOR');
});

test('rejects malformed addresses, same-address transfers, and non-integer amounts', () => {
  assert.throws(() => prepareNativePayment({ fromAddress: 'bad', toAddress: recipient, amountUqor: '1' }));
  assert.throws(() => prepareNativePayment({ fromAddress: sender, toAddress: sender, amountUqor: '1' }));
  for (const amountUqor of ['', '0', '-1', '1.2', '1e6', 100, true]) {
    assert.throws(() => prepareNativePayment({ fromAddress: sender, toAddress: recipient, amountUqor }));
  }
});

test('cannot open the wallet flow without an explicit owner click', async () => {
  const deps = stub({});
  await assert.rejects(requestOwnerReviewedPayment({ request: valid(), ownerClicked: false, ...deps }));
  assert.equal(deps.calls.length, 0);
});

test('encodes the prepared MsgSend and asks QoreX to review the Diana transaction', async () => {
  let partial;
  const MsgSend = {
    fromPartial: (value) => (partial = value),
    encode: (value) => ({ finish: () => Buffer.from(JSON.stringify(value)) }),
  };
  const deps = stub(MsgSend);
  const result = await requestOwnerReviewedPayment({ request: valid(), ownerClicked: true, ...deps });
  assert.deepEqual(partial, { fromAddress: sender, toAddress: recipient, amount: [{ denom: 'uqor', amount: '1250000' }] });
  assert.equal(deps.calls[0].chainId, 'qorechain-diana');
  assert.equal(deps.calls[0].messages[0].typeUrl, '/cosmos.bank.v1beta1.MsgSend');
  assert.equal(deps.calls[0].gasLimit, 300000);
  assert.deepEqual(result, { status: 'wallet_returned_tx', txHash: 'ABC123' });
});

test('does not invoke QoreX when unavailable and treats an owner decline as non-send', async () => {
  const unavailable = stub({});
  unavailable.adapter.hasQorexSignAndBroadcast = () => false;
  await assert.rejects(requestOwnerReviewedPayment({ request: valid(), ownerClicked: true, ...unavailable }));
  assert.equal(unavailable.calls.length, 0);

  const declined = stub({ fromPartial: (value) => value, encode: () => ({ finish: () => Buffer.from('x') }) });
  declined.adapter.qorexSignAndBroadcast = async () => { throw new Error('declined'); };
  declined.adapter.isQorexRejection = () => true;
  assert.deepEqual(await requestOwnerReviewedPayment({ request: valid(), ownerClicked: true, ...declined }), { status: 'declined' });
});
