import {
  addressFromPublicKey,
  deriveCanonicalPqKey,
  deriveClassicalKey,
  signMessage,
  verifyMessage,
} from "@qorechain/qoresign";

const PROTOCOL = "billguard.agent-message.demo.v1";
const FIELDS = ["version", "protocol", "chain_id", "message_id", "from", "to", "nonce", "issued_at", "expires_at", "body"];
const MAX_BODY_CHARS = 2048;

export function makeTestAgent(name, testOnlyMnemonic) {
  if (typeof name !== "string" || !name || typeof testOnlyMnemonic !== "string") {
    throw new TypeError("test agent name and test-only mnemonic are required");
  }
  const classicalKey = deriveClassicalKey({ mnemonic: testOnlyMnemonic });
  const signer = addressFromPublicKey(classicalKey.publicKey, "secp256k1").bech32;
  const pqKey = deriveCanonicalPqKey({ mnemonic: testOnlyMnemonic, address: signer });
  return Object.freeze({ name, signer, classicalKey, pqKey, pqPublicKey: pqKey.publicKey });
}

function canonicalPayload(payload) {
  // Rebuild in protocol-defined order so object key order in received JSON is irrelevant.
  return JSON.stringify(Object.fromEntries(FIELDS.map((field) => [field, payload[field]])));
}

export function createMessageEnvelope({ sender, recipient, chainId, messageId, nonce, issuedAt, expiresAt, body }) {
  if (!sender?.classicalKey || !sender?.pqKey || !recipient?.signer) throw new TypeError("sender and recipient identities are required");
  const payload = { version: 1, protocol: PROTOCOL, chain_id: chainId, message_id: messageId,
    from: sender.signer, to: recipient.signer, nonce, issued_at: issuedAt, expires_at: expiresAt, body };
  validatePayload(payload);
  const signature = signMessage({ chainId, signer: sender.signer, data: canonicalPayload(payload),
    classicalKey: sender.classicalKey, pqKey: sender.pqKey });
  return { payload, signature };
}

function validatePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)
      || Object.keys(payload).length !== FIELDS.length || FIELDS.some((field) => !Object.hasOwn(payload, field))) {
    throw new Error("invalid message fields");
  }
  if (payload.version !== 1 || payload.protocol !== PROTOCOL) throw new Error("unsupported message protocol");
  for (const field of ["chain_id", "message_id", "from", "to", "nonce", "body"]) {
    if (typeof payload[field] !== "string" || payload[field].length === 0) throw new Error(`invalid ${field}`);
  }
  if (payload.body.length > MAX_BODY_CHARS) throw new Error("message body exceeds limit");
  if (!Number.isSafeInteger(payload.issued_at) || !Number.isSafeInteger(payload.expires_at)) throw new Error("invalid message times");
}

export function receiveMessageEnvelope(envelope, { receiver, trustedPeer, chainId, now,
  seenNonces, maxTtlSeconds = 300, clockSkewSeconds = 5 }) {
  if (!receiver?.signer || !trustedPeer?.signer || !trustedPeer?.pqPublicKey) throw new Error("receiver and trusted peer identities are required");
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(maxTtlSeconds) || maxTtlSeconds <= 0
      || !Number.isSafeInteger(clockSkewSeconds) || clockSkewSeconds < 0) throw new Error("invalid verifier time policy");
  if (!(seenNonces instanceof Set)) throw new Error("replay store must be a Set");
  if (!envelope || typeof envelope !== "object" || Array.isArray(envelope)
      || Object.keys(envelope).length !== 2 || !Object.hasOwn(envelope, "payload") || !Object.hasOwn(envelope, "signature")) {
    throw new Error("invalid envelope fields");
  }
  const { payload, signature } = envelope;
  validatePayload(payload);
  if (payload.chain_id !== chainId) throw new Error("wrong chain");
  if (payload.from !== trustedPeer.signer) throw new Error("wrong signer");
  if (payload.to !== receiver.signer) throw new Error("wrong recipient");
  if (payload.issued_at > now + clockSkewSeconds) throw new Error("message issued in the future");
  if (payload.expires_at <= now || payload.expires_at <= payload.issued_at) throw new Error("message expired or invalid expiry");
  if (payload.expires_at - payload.issued_at > maxTtlSeconds) throw new Error("message lifetime exceeds policy");
  if (!signature || typeof signature !== "object") throw new Error("missing signature");
  verifyMessage({ chainId, signer: trustedPeer.signer, data: canonicalPayload(payload), signature,
    pqPublicKey: trustedPeer.pqPublicKey });
  const replayKey = `${trustedPeer.signer}:${payload.nonce}`;
  if (seenNonces.has(replayKey)) throw new Error("replayed message nonce");
  // In-memory demo only. Production needs durable, atomic replay protection shared by all receivers.
  seenNonces.add(replayKey);
  return Object.freeze({ ...payload });
}
