import test from "node:test";
import assert from "node:assert/strict";
import { createMessageEnvelope, makeTestAgent, receiveMessageEnvelope } from "../two_agent.mjs";

const CHAIN = "qorechain-diana";
// Public BIP-39 test vectors only; never use these mnemonics for funds.
const agentA = makeTestAgent("Agent A", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about");
const agentB = makeTestAgent("Agent B", "legal winner thank year wave sausage worth useful legal winner thank yellow");
const base = { sender: agentA, recipient: agentB, chainId: CHAIN, messageId: "msg-a-001",
  nonce: "nonce-agent-a-0001", issuedAt: 1000, expiresAt: 1120, body: "propose payment preview only" };
function signed(overrides = {}) { return createMessageEnvelope({ ...base, ...overrides }); }
const receiverContext = (now = 1050, seenNonces = new Set(), trustedPeer = agentA) => ({
  receiver: agentB, trustedPeer, chainId: CHAIN, now, seenNonces,
});

test("two local agents exchange QoreSign-signed messages in both directions", () => {
  const aToB = signed();
  const acceptedByB = receiveMessageEnvelope(aToB, receiverContext());
  assert.equal(acceptedByB.body, base.body);
  const bToA = createMessageEnvelope({ sender: agentB, recipient: agentA, chainId: CHAIN,
    messageId: "msg-b-001", nonce: "nonce-agent-b-0001", issuedAt: 1050, expiresAt: 1170, body: "received and verified" });
  const acceptedByA = receiveMessageEnvelope(bToA, { receiver: agentA, trustedPeer: agentB, chainId: CHAIN,
    now: 1075, seenNonces: new Set() });
  assert.equal(acceptedByA.body, "received and verified");
});

test("changed body or tampered signature is rejected", () => {
  const message = signed();
  const changed = structuredClone(message);
  changed.payload.body += "!";
  assert.throws(() => receiveMessageEnvelope(changed, receiverContext()), /signature|invalid/i);
  const badSignature = structuredClone(message);
  badSignature.signature.classical.signature = "00";
  assert.throws(() => receiveMessageEnvelope(badSignature, receiverContext()));
});

test("wrong trusted signer and wrong recipient are rejected", () => {
  const message = signed();
  assert.throws(() => receiveMessageEnvelope(message, receiverContext(1050, new Set(), agentB)), /wrong signer/i);
  const misaddressed = signed({ recipient: agentA });
  assert.throws(() => receiveMessageEnvelope(misaddressed, receiverContext()), /wrong recipient/i);
});

test("expired and future-dated messages are rejected", () => {
  assert.throws(() => receiveMessageEnvelope(signed(), receiverContext(1120)), /expired/i);
  assert.throws(() => receiveMessageEnvelope(signed({ issuedAt: 2000, expiresAt: 2100 }), receiverContext(1050)), /future/i);
});

test("message nonce is consumed only once after successful verification", () => {
  const message = signed();
  const seen = new Set();
  receiveMessageEnvelope(message, receiverContext(1050, seen));
  assert.throws(() => receiveMessageEnvelope(message, receiverContext(1050, seen)), /replayed/i);
});

test("expired/rejected message does not consume its nonce", () => {
  const message = signed();
  const seen = new Set();
  assert.throws(() => receiveMessageEnvelope(message, receiverContext(1200, seen)), /expired/i);
  assert.equal(seen.size, 0);
});

test("wrong chain, oversized body, malformed schema and excessive TTL are rejected", () => {
  assert.throws(() => receiveMessageEnvelope(signed(), { ...receiverContext(), chainId: "qorechain-other" }), /wrong chain/i);
  assert.throws(() => signed({ body: "x".repeat(2049) }), /body exceeds/i);
  const extra = signed(); extra.payload.extra = true;
  assert.throws(() => receiveMessageEnvelope(extra, receiverContext()), /invalid message fields/i);
  assert.throws(() => receiveMessageEnvelope(signed({ expiresAt: 1400 }), receiverContext()), /lifetime exceeds/i);
});
