import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const worker = path.join(here, "loopback_agent.mjs");
const env = { PATH: process.env.PATH, HOME: process.env.HOME };

async function freeLoopbackPort() {
  const server = createServer();
  await new Promise((resolve, reject) => server.once("error", reject).listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return port;
}
function start(role, port, peerPort, peerRole) {
  const child = spawn(process.execPath, [worker, role, String(port), String(peerPort), peerRole], { cwd: here, env, stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
  const lines = createInterface({ input: child.stdout });
  const ready = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${role} did not start`)), 5000);
    lines.on("line", (line) => {
      try {
        const event = JSON.parse(line);
        if (event.event === "ready") { clearTimeout(timer); resolve(event); }
      } catch { /* ignore non-JSON diagnostic lines */ }
    });
    child.once("error", (error) => { clearTimeout(timer); reject(error); });
    child.once("exit", (code) => { if (code !== 0) { clearTimeout(timer); reject(new Error(`${role} exited ${code}: ${stderr}`)); } });
  });
  return { child, ready };
}
async function stop(children) {
  await Promise.all(children.map(({ child }) => new Promise((resolve) => {
    if (child.exitCode !== null) return resolve();
    child.once("exit", resolve);
    child.kill("SIGTERM");
    setTimeout(() => { if (child.exitCode === null) child.kill("SIGKILL"); }, 1000).unref();
  })));
}
async function send(port, body) {
  const response = await fetch(`http://127.0.0.1:${port}/send`, { method: "POST",
    headers: { "content-type": "application/json" }, body: JSON.stringify({ body }) });
  return { status: response.status, value: await response.json() };
}

const portA = await freeLoopbackPort();
let portB = await freeLoopbackPort();
while (portB === portA) portB = await freeLoopbackPort();
const children = [start("agent-b", portB, portA, "agent-a"), start("agent-a", portA, portB, "agent-b")];
try {
  await Promise.all(children.map(({ ready }) => ready));
  const aToB = await send(portA, "BillGuard preview: payment candidate only; no transaction submitted.");
  if (aToB.status !== 200 || !aToB.value.peer_result?.accepted) throw new Error("Agent B did not accept Agent A's signed message");
  const proposal = { type: "billguard.payment_proposal.local.v1", payment: {
    sender: "0x1111111111111111111111111111111111111111",
    recipient: "0x2222222222222222222222222222222222222222",
    amount_uqor: 700000, max_fee_uqor: 50000, denom: "uqor", calldata: "0x",
  } };
  const payment = await send(portA, JSON.stringify(proposal));
  if (payment.status !== 200 || !payment.value.peer_result?.payment_decision?.accepted) {
    throw new Error("Agent B did not accept the signed proposal under the local simulated caps");
  }
  const declined = await send(portA, JSON.stringify({ ...proposal, payment: {
    ...proposal.payment, recipient: "0x3333333333333333333333333333333333333333",
  } }));
  if (declined.status !== 200 || declined.value.peer_result?.payment_decision?.accepted !== false) {
    throw new Error("Agent B did not reject the out-of-scope recipient");
  }
  const bToA = await send(portB, "Agent A's signed message received; no transaction submitted.");
  if (bToA.status !== 200 || !bToA.value.peer_result?.accepted) throw new Error("Agent A did not accept Agent B's signed reply");
  console.log(JSON.stringify({
    transport: "HTTP over 127.0.0.1; two separate local Node processes",
    agent_a_to_b: aToB.value.peer_result.accepted,
    agent_b_to_a: bToA.value.peer_result.accepted,
    signed_payment_proposal: payment.value.peer_result.payment_decision.accepted,
    simulated_outflow_uqor: payment.value.peer_result.payment_decision.plan.payment.worst_case_outflow_uqor,
    out_of_scope_target_rejected: !declined.value.peer_result.payment_decision.accepted,
    limits: "local fixed caps only; no on-chain enforcement or bounty proof",
    chain_id: "qorechain-diana", transaction_sent: false,
  }, null, 2));
} finally { await stop(children); }
