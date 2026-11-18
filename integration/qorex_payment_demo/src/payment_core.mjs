/**
 * Pure request construction for the QoreX owner-controlled Diana demo.
 * This module never talks to a wallet or network.
 */
export const QORECHAIN_DIANA = 'qorechain-diana';
export const NATIVE_DENOM = 'uqor';
export const DEFAULT_GAS_LIMIT = 300_000;

const QOR_ADDRESS = /^qor1[023456789acdefghjklmnpqrstuvwxyz]{38,58}$/;

export function prepareNativePayment({ fromAddress, toAddress, amountUqor }) {
  if (typeof fromAddress !== 'string' || !QOR_ADDRESS.test(fromAddress)) {
    throw new TypeError('Enter a syntactically valid lowercase qor1 address for the sender.');
  }
  if (typeof toAddress !== 'string' || !QOR_ADDRESS.test(toAddress)) {
    throw new TypeError('Enter a syntactically valid lowercase qor1 address for the recipient.');
  }
  if (fromAddress === toAddress) throw new TypeError('Sender and recipient must be different.');
  if (typeof amountUqor !== 'string' || !/^[0-9]{1,78}$/.test(amountUqor)) {
    throw new TypeError('Amount must be a positive whole number of uqor, entered as digits.');
  }
  if (BigInt(amountUqor) <= 0n) throw new TypeError('Amount must be greater than zero.');

  return Object.freeze({
    chainId: QORECHAIN_DIANA,
    fromAddress,
    toAddress,
    amount: Object.freeze([{ denom: NATIVE_DENOM, amount: amountUqor }]),
    gasLimit: DEFAULT_GAS_LIMIT,
    ownerApprovalRequired: true,
  });
}

export function formatQor(amountUqor) {
  const amount = BigInt(amountUqor);
  const whole = amount / 1_000_000n;
  const fractional = (amount % 1_000_000n).toString().padStart(6, '0').replace(/0+$/, '');
  return fractional ? `${whole}.${fractional} QOR` : `${whole} QOR`;
}

/**
 * Invoke only from a deliberate owner click. QoreX itself displays the decoded
 * transaction and performs the signing/broadcast only if its owner approves.
 */
export async function requestOwnerReviewedPayment({ request, ownerClicked, adapter, MsgSend }) {
  if (ownerClicked !== true) throw new Error('A separate owner click is required before opening QoreX.');
  if (!request || request.ownerApprovalRequired !== true || request.chainId !== QORECHAIN_DIANA) {
    throw new Error('Prepare a Diana owner-reviewed payment request first.');
  }
  if (!adapter || typeof adapter.hasQorexSignAndBroadcast !== 'function' ||
      !adapter.hasQorexSignAndBroadcast()) {
    throw new Error('QoreX is not available. Install or update QoreX and select Diana there.');
  }
  if (!MsgSend || typeof MsgSend.fromPartial !== 'function' ||
      typeof MsgSend.encode !== 'function') {
    throw new Error('The Cosmos MsgSend encoder is unavailable.');
  }

  const message = MsgSend.fromPartial({
    fromAddress: request.fromAddress,
    toAddress: request.toAddress,
    amount: request.amount.map((coin) => ({ ...coin })),
  });
  try {
    const result = await adapter.qorexSignAndBroadcast({
      chainId: QORECHAIN_DIANA,
      messages: [{ typeUrl: '/cosmos.bank.v1beta1.MsgSend', value: MsgSend.encode(message).finish() }],
      gasLimit: request.gasLimit,
    });
    if (!result || result.code !== 0 || typeof result.txHash !== 'string' || !result.txHash) {
      throw new Error('QoreX did not return a successful transaction result.');
    }
    return { status: 'wallet_returned_tx', txHash: result.txHash };
  } catch (error) {
    if (typeof adapter.isQorexRejection === 'function' && adapter.isQorexRejection(error)) {
      return { status: 'declined' };
    }
    throw error;
  }
}
