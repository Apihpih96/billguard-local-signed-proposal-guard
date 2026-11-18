import {
  addressFromPublicKey,
  deriveCanonicalPqKey,
  deriveClassicalKey,
  signMessage,
  verifyMessage,
} from "@qorechain/qoresign";

// Public BIP-39 test vector only; never use this mnemonic for a funded account.
const testOnlyMnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";
const chainId = "qorechain-diana";
const classicalKey = deriveClassicalKey({ mnemonic: testOnlyMnemonic });
const signer = addressFromPublicKey(classicalKey.publicKey, "secp256k1").bech32;
const pqKey = deriveCanonicalPqKey({ mnemonic: testOnlyMnemonic, address: signer });

// This is a local sample instruction, not a transaction or real payment request.
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

const signature = signMessage({ chainId, signer, data: instruction, classicalKey, pqKey });
// Local test fixture stands in for the PQ public key a real verifier must fetch
// and authenticate from QoreChain's registered-key endpoint.
verifyMessage({ chainId, signer, data: instruction, signature, pqPublicKey: pqKey.publicKey });

console.log(JSON.stringify({
  demo: "QoreSign v0.1.1 ADR-36 + ML-DSA-87 off-chain message",
  chain_id: chainId,
  signer,
  instruction,
  signature_type: signature.signatureType,
  algorithm_id: signature.pq?.algorithmId,
  verified: true,
  registered_key_lookup: "not performed; local public test key used",
  network_access: "none",
}, null, 2));
