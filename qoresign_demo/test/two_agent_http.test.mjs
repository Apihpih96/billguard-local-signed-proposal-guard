import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createMessageEnvelope, makeTestAgent } from "../two_agent.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const worker = path.join(here, "..", "loopback_agent.mjs");
const CHAIN = "qorechain-diana";
const MNEMONICS = {
  "agent-a": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
  "agent-b": "legal winner thank year wave sausage worth useful legal winner thank yellow",
  "agent-c": "letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
};
const agents = Object.fromEntries(Object.entries(MNEMONICS).map(([name, phrase]) => [name, makeTestAgent(name, phrase)]));
const env = { PATH: process.env.PATH, HOME: process.env.HOME };

async function freePort() {
  const server = createServer();
  await new Promise((resolve, reject) => server.once("error", reject).listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return port;
}
function start(role, port, peerPort, peerRole) {
  const child = spawn(process.execPath, [worker, role, String(port), String(peerPort), peerRole], { cwd: path.dirname(worker), env, stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
  const lines = createInterface({ input: child.stdout });
  const ready = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${role} startup timed out: ${stderr}`)), 5000);
    lines.on("line", (line) => {
      try { const value = JSON.parse(line); if (value.event === "ready") { clearTimeout(timer); resolve(value); } }
      catch { /* ignore */ }
    });
    child.once("error", (error) => { clearTimeout(timer); reject(error); });
    child.once("exit", (code) => { if (code !== 0) { clearTimeout(timer); reject(new Error(`${role} exited ${code}: ${stderr}`)); } });
  });
  return { child, ready };
}
async function stopAll(children) {
  await Promise.all(children.map(({ child }) => new Promise((resolve) => {
    if (child.exitCode !== null) return resolve();
    child.once("exit", resolve); child.kill("SIGTERM");
    setTimeout(() => { if (child.exitCode === null) child.kill("SIGKILL"); }, 1000).unref();
  })));
}
async function post(port, route, value) {
  const response = await fetch(`http://127.0.0.1:${port}${route}`, { method: "POST",
    headers: { "content-type": "application/json" }, body: JSON.stringify(value) });
  return { status: response.status, value: await response.json() };
}
function paymentProposal({ recipient = "0x2222222222222222222222222222222222222222", amount = 700_000, fee = 50_000 } = {}) {
  return JSON.stringify({ type: "billguard.payment_proposal.local.v1", payment: {
    sender: "0x1111111111111111111111111111111111111111", recipient,
    amount_uqor: amount, max_fee_uqor: fee, denom: "uqor", calldata: "0x",
  } });
}
function assertNoApprovalOrExecution(value) {
  if (Array.isArray(value)) return value.forEach(assertNoApprovalOrExecution);
  if (!value || typeof value !== "object") return;
  for (const [key, nested] of Object.entries(value)) {
    assert.ok(!["approval", "approved", "execution", "signing_performed", "broadcast_performed", "chain_state_changed"].includes(key),
      `unexpected approval/execution field: ${key}`);
    assertNoApprovalOrExecution(nested);
  }
}

// Public BIP-39 test vectors only; these identities are deliberately insecure and unfunded.
test("separate local agent processes exchange hybrid-signed HTTP envelopes and reject attacks", async (t) => {
  const ports = [];
  while (ports.length < 3) { const candidate = await freePort(); if (!ports.includes(candidate)) ports.push(candidate); }
  const [portA, portB, portC] = ports;
  const children = [
    start("agent-a", portA, portB, "agent-b"),
    start("agent-b", portB, portA, "agent-a"),
    start("agent-c", portC, portB, "agent-b"),
  ];
  t.after(() => stopAll(children));
  const started = await Promise.all(children.map(({ ready }) => ready));
  assert.deepEqual(started.map((item) => item.host), ["127.0.0.1", "127.0.0.1", "127.0.0.1"]);

  const first = await post(portA, "/send", { body: "Agent A asks for a bounded payment preview." });
  assert.equal(first.status, 200);
  assert.equal(first.value.sent, true);
  assert.equal(first.value.peer_result.accepted, true);
  assert.equal(first.value.peer_result.from, agents["agent-a"].signer);
  assert.equal(first.value.peer_result.to, agents["agent-b"].signer);

  const reply = await post(portB, "/send", { body: "Agent B acknowledges the signed preview." });
  assert.equal(reply.status, 200);
  assert.equal(reply.value.peer_result.accepted, true);

  const goodProposal = await post(portA, "/send", { body: paymentProposal() });
  assert.equal(goodProposal.status, 200);
  assert.equal(goodProposal.value.peer_result.accepted, true, "signature validation accepts the authenticated proposal");
  assert.equal(goodProposal.value.peer_result.payment_decision.accepted, true);
  assert.equal(goodProposal.value.peer_result.payment_decision.plan.payment.worst_case_outflow_uqor, 750_000);
  assert.equal(goodProposal.value.peer_result.payment_decision.plan.execution.executable, false);
  assert.equal(goodProposal.value.peer_result.payment_decision.plan.execution.signing_performed, false);
  assert.equal(goodProposal.value.peer_result.payment_decision.plan.execution.broadcast_performed, false);
  assert.equal(goodProposal.value.peer_result.payment_decision.plan.checks.owner_exact_review_required_before_any_live_transaction, true);

  const wrongTarget = await post(portA, "/send", { body: paymentProposal({ recipient: "0x3333333333333333333333333333333333333333" }) });
  assert.equal(wrongTarget.status, 200, "an authentic message can still be declined by local policy");
  assert.equal(wrongTarget.value.peer_result.accepted, true);
  assert.equal(wrongTarget.value.peer_result.payment_decision.accepted, false);
  assert.match(wrongTarget.value.peer_result.payment_decision.reason, /recipient does not match/i);
  assertNoApprovalOrExecution(wrongTarget.value.peer_result.payment_decision);
  assert.equal(Object.hasOwn(wrongTarget.value.peer_result.payment_decision, "plan"), false);

  const overTransactionCap = await post(portA, "/send", { body: paymentProposal({ amount: 900_000, fee: 50_000 }) });
  assert.equal(overTransactionCap.status, 200);
  assert.equal(overTransactionCap.value.peer_result.payment_decision.accepted, false);
  assert.match(overTransactionCap.value.peer_result.payment_decision.reason, /per-transaction cap/i);
  assertNoApprovalOrExecution(overTransactionCap.value.peer_result.payment_decision);
  assert.equal(Object.hasOwn(overTransactionCap.value.peer_result.payment_decision, "plan"), false);

  const overWindowCap = await post(portA, "/send", { body: paymentProposal({ amount: 980_000, fee: 50_000 }) });
  assert.equal(overWindowCap.status, 200);
  assert.equal(overWindowCap.value.peer_result.payment_decision.accepted, false);
  assert.match(overWindowCap.value.peer_result.payment_decision.reason, /EVM window cap/i);
  assertNoApprovalOrExecution(overWindowCap.value.peer_result.payment_decision);
  assert.equal(Object.hasOwn(overWindowCap.value.peer_result.payment_decision, "plan"), false);

  const replay = await post(portB, "/message", first.value.envelope);
  assert.equal(replay.status, 400);
  assert.match(replay.value.error, /replayed/i);
  assertNoApprovalOrExecution(replay.value);
  assert.equal(Object.hasOwn(replay.value, "payment_decision"), false, "replay is rejected before policy evaluation");

  const tampered = structuredClone(first.value.envelope);
  tampered.payload.body += " tampered";
  const tamperResult = await post(portB, "/message", tampered);
  assert.equal(tamperResult.status, 400);
  assert.match(tamperResult.value.error, /signature/i);
  assertNoApprovalOrExecution(tamperResult.value);
  assert.equal(Object.hasOwn(tamperResult.value, "payment_decision"), false, "tampering is rejected before policy evaluation");

  const wrongSigner = await post(portC, "/send", { body: "Untrusted agent C message." });
  assert.equal(wrongSigner.status, 400);
  assert.match(wrongSigner.value.peer_result.error, /wrong signer/i);
  assertNoApprovalOrExecution(wrongSigner.value.peer_result);
  assert.equal(Object.hasOwn(wrongSigner.value.peer_result, "payment_decision"), false, "untrusted signer is rejected before policy evaluation");

  const now = Math.floor(Date.now() / 1000);
  const expired = createMessageEnvelope({ sender: agents["agent-a"], recipient: agents["agent-b"], chainId: CHAIN,
    messageId: "expired-local-http-message", nonce: "expired-local-http-nonce", issuedAt: now - 400, expiresAt: now - 1, body: "expired" });
  const expiredResult = await post(portB, "/message", expired);
  assert.equal(expiredResult.status, 400);
  assert.match(expiredResult.value.error, /expired/i);
  assertNoApprovalOrExecution(expiredResult.value);
  assert.equal(Object.hasOwn(expiredResult.value, "payment_decision"), false, "expired envelope is rejected before policy evaluation");
});
