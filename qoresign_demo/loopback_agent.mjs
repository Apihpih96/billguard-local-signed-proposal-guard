import { createServer } from "node:http";
import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import { makeTestAgent, createMessageEnvelope, receiveMessageEnvelope } from "./two_agent.mjs";

const CHAIN_ID = "qorechain-diana";
const MAX_REQUEST_BYTES = 16 * 1024;
const MAX_BODY_CHARS = 2048;
const POLICY_GUARD = new URL("../integration/local_proposal_guard.py", import.meta.url);
const PROPOSAL_TYPE = "billguard.payment_proposal.local.v1";
const TEST_MNEMONICS = Object.freeze({
  "agent-a": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
  "agent-b": "legal winner thank year wave sausage worth useful legal winner thank yellow",
  "agent-c": "letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
});

function fail(message) { throw new Error(message); }
function parsePort(value, label) {
  if (!/^\d+$/.test(value ?? "")) fail(`invalid ${label}`);
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65535) fail(`invalid ${label}`);
  return port;
}

const [role, rawPort, rawPeerPort, peerRole] = process.argv.slice(2);
if (!Object.hasOwn(TEST_MNEMONICS, role) || !Object.hasOwn(TEST_MNEMONICS, peerRole) || role === peerRole) {
  fail("usage: node loopback_agent.mjs <agent-a|agent-b|agent-c> <port> <peer-port> <different-peer-role>");
}
const port = parsePort(rawPort, "listen port");
const peerPort = parsePort(rawPeerPort, "peer port");
const agent = makeTestAgent(role, TEST_MNEMONICS[role]);
const peer = makeTestAgent(peerRole, TEST_MNEMONICS[peerRole]);
const seenNonces = new Set();

function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "content-length": Buffer.byteLength(body) });
  res.end(body);
}
async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_REQUEST_BYTES) throw new Error("request body too large");
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString("utf8");
  return JSON.parse(text);
}
function isLoopback(address) {
  return address === "127.0.0.1" || address === "::1" || address === "::ffff:127.0.0.1";
}

function checkPaymentProposal(body) {
  let proposal;
  try { proposal = JSON.parse(body); }
  catch { return null; }
  if (!proposal || typeof proposal !== "object" || Array.isArray(proposal)
      || proposal.type !== PROPOSAL_TYPE) return null;
  if (Object.keys(proposal).length !== 2 || !Object.hasOwn(proposal, "payment")) {
    return { accepted: false, reason: "proposal must contain only type and payment" };
  }
  const result = spawnSync("python3", [POLICY_GUARD.pathname], {
    input: JSON.stringify({ payment: proposal.payment }), encoding: "utf8", timeout: 3000,
    maxBuffer: 64 * 1024, cwd: new URL("..", import.meta.url).pathname,
  });
  if (result.error || result.status !== 0) {
    return { accepted: false, reason: "local policy checker unavailable; failed closed" };
  }
  try {
    const checked = JSON.parse(result.stdout);
    if (checked?.accepted === true && checked.plan?.execution?.executable === false) {
      return { accepted: true, plan: checked.plan };
    }
    if (checked?.accepted === false && typeof checked.reason === "string") {
      return { accepted: false, reason: checked.reason };
    }
  } catch { /* fail closed below */ }
  return { accepted: false, reason: "local policy checker returned an invalid result" };
}

const server = createServer(async (req, res) => {
  if (!isLoopback(req.socket.remoteAddress)) return json(res, 403, { error: "loopback clients only" });
  if (req.method === "GET" && req.url === "/health") return json(res, 200, { ready: true, role });
  if (req.method !== "POST" || !["/message", "/send"].includes(req.url)) return json(res, 404, { error: "not found" });
  if (!/^application\/json(?:\s*;|$)/i.test(req.headers["content-type"] ?? "")) return json(res, 415, { error: "application/json required" });
  try {
    const value = await readJson(req);
    if (req.url === "/message") {
      const accepted = receiveMessageEnvelope(value, { receiver: agent, trustedPeer: peer, chainId: CHAIN_ID,
        now: Math.floor(Date.now() / 1000), seenNonces });
      const result = { accepted: true, message_id: accepted.message_id, from: accepted.from, to: accepted.to, body: accepted.body };
      const paymentDecision = checkPaymentProposal(accepted.body);
      if (paymentDecision !== null) result.payment_decision = paymentDecision;
      return json(res, 200, result);
    }

    if (!value || typeof value !== "object" || Array.isArray(value) || typeof value.body !== "string"
        || value.body.length === 0 || value.body.length > MAX_BODY_CHARS
        || Object.keys(value).some((key) => !["body"].includes(key))) {
      throw new Error("send request must contain only a non-empty body of at most 2048 characters");
    }
    const now = Math.floor(Date.now() / 1000);
    const envelope = createMessageEnvelope({ sender: agent, recipient: peer, chainId: CHAIN_ID,
      messageId: randomUUID(), nonce: randomUUID(), issuedAt: now, expiresAt: now + 120, body: value.body });
    const peerResponse = await fetch(`http://127.0.0.1:${peerPort}/message`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(envelope),
    });
    let peerResult;
    try { peerResult = await peerResponse.json(); } catch { peerResult = { error: "peer returned invalid JSON" }; }
    return json(res, peerResponse.status, { sent: peerResponse.ok, envelope, peer_status: peerResponse.status, peer_result: peerResult });
  } catch (error) {
    return json(res, 400, { error: error instanceof Error ? error.message : "invalid request" });
  }
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`${JSON.stringify({ event: "ready", role, port, host: "127.0.0.1" })}\n`);
});
server.on("error", (error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
