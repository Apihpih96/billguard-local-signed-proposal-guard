import { MsgSend } from 'cosmjs-types/cosmos/bank/v1beta1/tx.js';
import {
  hasQorexSignAndBroadcast,
  qorexSignAndBroadcast,
  isQorexRejection,
} from '@qorechain/wallet-adapter';
import { formatQor, prepareNativePayment, requestOwnerReviewedPayment } from './payment_core.mjs';

const form = document.querySelector('#payment-form');
const sender = document.querySelector('#sender');
const recipient = document.querySelector('#recipient');
const amount = document.querySelector('#amount');
const review = document.querySelector('#review');
const status = document.querySelector('#status');
const submit = document.querySelector('#open-wallet');
let request = null;

const adapter = { hasQorexSignAndBroadcast, qorexSignAndBroadcast, isQorexRejection };

form.addEventListener('submit', (event) => {
  event.preventDefault();
  status.textContent = '';
  try {
    request = prepareNativePayment({
      fromAddress: sender.value,
      toAddress: recipient.value,
      amountUqor: amount.value,
    });
    review.textContent = `Diana · ${formatQor(amount.value)} · ${request.fromAddress} → ${request.toAddress}`;
    submit.disabled = false;
    status.textContent = 'Prepared only. Nothing has been signed or sent.';
  } catch (error) {
    request = null;
    submit.disabled = true;
    review.textContent = '';
    status.textContent = error.message;
  }
});

submit.addEventListener('click', async () => {
  if (!request || submit.disabled) return;
  submit.disabled = true;
  status.textContent = 'Opening QoreX for its owner review…';
  try {
    const result = await requestOwnerReviewedPayment({
      request,
      ownerClicked: true,
      adapter,
      MsgSend,
    });
    status.textContent = result.status === 'declined'
      ? 'You declined in QoreX; no transfer was sent.'
      : `QoreX returned transaction hash ${result.txHash}. Check the Diana explorer before treating it as final.`;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});
