import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  QoreSignError,
  addressFromPublicKey,
  deriveCanonicalPqKey,
  deriveClassicalKey,
  fromHex,
  messagePqSignBytes,
  signMessage,
  verifyMessage,
} from "@qorechain/qoresign";

const testOnlyMnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";
const chainId = "qorechain-diana";
const classicalKey = deriveClassicalKey({ mnemonic: testOnlyMnemonic });
const signer = addressFromPublicKey(classicalKey.publicKey, "secp256k1").bech32;
const pqKey = deriveCanonicalPqKey({ mnemonic: testOnlyMnemonic, address: signer });
const instruction = JSON.stringify({
  protocol: "billguard.agent-instruction.demo.v1",
  chain_id: chainId,
  message_id: "demo-001",
  action: "pay_native",
  recipient: "DEMO-ONLY-RECIPIENT",
  amount_uqor: "10000",
  max_fee_uqor: "1000",
  expires_at_height: 1000,
});
const messageSignature = signMessage({ chainId, signer, data: instruction, classicalKey, pqKey });

function errorCode(fn) {
  try { fn(); } catch (error) { return error instanceof QoreSignError ? error.code : "unknown"; }
  return undefined;
}

test("demo instruction is signed and verified by official QoreSign hybrid API", () => {
  assert.equal(messageSignature.signatureType, "ml-dsa-87-hybrid");
  assert.equal(messageSignature.pq.algorithmId, 1);
  assert.doesNotThrow(() => verifyMessage({ chainId, signer, data: instruction, signature: messageSignature, pqPublicKey: pqKey.publicKey }));
});

test("official QoreSign v0.1.1 message vector verifies", () => {
  const vector = JSON.parse(readFileSync(new URL("./official-message-vector.json", import.meta.url), "utf8"));
  assert.equal(vector.signer, signer);
  const signature = vector.case.signature;
  assert.equal(signature.signatureType, "ml-dsa-87-hybrid");
  assert.doesNotThrow(() => verifyMessage({
    chainId: vector.chainId,
    signer: vector.signer,
    data: fromHex(vector.case.data),
    signature,
    pqPublicKey: fromHex(vector.pqPublicKey),
  }));
});

test("QoreSign rejects message and chain tampering", () => {
  assert.equal(errorCode(() => verifyMessage({ chainId, signer, data: `${instruction}!`, signature: messageSignature, pqPublicKey: pqKey.publicKey })), "CLASSICAL_SIGNATURE_INVALID");
  assert.equal(errorCode(() => verifyMessage({ chainId: "qorechain-other", signer, data: instruction, signature: messageSignature, pqPublicKey: pqKey.publicKey })), "PQ_SIGNATURE_INVALID");
});

test("QoreSign rejects a different or missing registered PQ key", () => {
  const otherPqKey = deriveCanonicalPqKey({ mnemonic: testOnlyMnemonic, address: "qor1npvwllfr9dqr8erajqqr6s0vxnk2ak55am9g2c" });
  assert.equal(errorCode(() => verifyMessage({ chainId, signer, data: instruction, signature: messageSignature, pqPublicKey: otherPqKey.publicKey })), "PQ_SIGNATURE_INVALID");
  assert.equal(errorCode(() => verifyMessage({ chainId, signer, data: instruction, signature: messageSignature })), "KEY_NOT_REGISTERED");
});

test("PQ message bytes use the official domain and chain prefix", () => {
  assert.deepEqual(
    Buffer.from(messagePqSignBytes(chainId, "hello")),
    Buffer.from(`qorechain-msg-v1|${chainId}|hello`, "utf8"),
  );
});
