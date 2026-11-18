import { createMessageEnvelope, makeTestAgent, receiveMessageEnvelope } from "./two_agent.mjs";

const chainId = "qorechain-diana";
const agentA = makeTestAgent("Agent A", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about");
const agentB = makeTestAgent("Agent B", "legal winner thank year wave sausage worth useful legal winner thank yellow");
const seenAtB = new Set();
const seenAtA = new Set();
const first = createMessageEnvelope({ sender: agentA, recipient: agentB, chainId,
  messageId: "local-msg-001", nonce: "agent-a-nonce-0001", issuedAt: 1_800_000_000,
  expiresAt: 1_800_000_120, body: "Propose a capped payment preview; do not execute." });
const received = receiveMessageEnvelope(first, { receiver: agentB, trustedPeer: agentA,
  chainId, now: 1_800_000_030, seenNonces: seenAtB });
const reply = createMessageEnvelope({ sender: agentB, recipient: agentA, chainId,
  messageId: "local-msg-002", nonce: "agent-b-nonce-0001", issuedAt: 1_800_000_030,
  expiresAt: 1_800_000_150, body: "Received and authenticated locally." });
const acknowledged = receiveMessageEnvelope(reply, { receiver: agentA, trustedPeer: agentB,
  chainId, now: 1_800_000_060, seenNonces: seenAtA });

console.log(JSON.stringify({
  demo: "two local agents using QoreSign v0.1.1 off-chain hybrid signatures",
  transport: "in-memory function handoff; no network or agent messaging service",
  message_envelope_fields: Object.keys(first.payload),
  round_trip: [
    { from: agentA.name, to: agentB.name, locally_verified: received.body === first.payload.body },
    { from: agentB.name, to: agentA.name, locally_verified: acknowledged.body === reply.payload.body },
  ],
  replay_protection: "per-process Set only; not durable or distributed",
  test_keys: "public BIP-39 test vectors; never use for funds",
  limitations: [
    "sender trust is preconfigured with local test public keys, not fetched from chain",
    "expiry and replay checks are application-level demo logic",
    "not live agent-to-agent network messaging or proof of bounty compliance",
  ],
}, null, 2));
