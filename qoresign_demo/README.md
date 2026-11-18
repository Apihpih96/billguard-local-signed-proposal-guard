# QoreSign v0.1.1 local off-chain message demo

This uses the official `@qorechain/qoresign` package pinned to 0.1.1 and upstream tag `go/v0.1.1` (commit `be7b85ac1b8be0cfc5fabf2cc7bd40bd43141f6c`). The protocol source is [`spec/message-signing-v1.md`](https://github.com/qorechain/qoresign/blob/go/v0.1.1/spec/message-signing-v1.md).

Run on Node.js 20+: `corepack pnpm install --frozen-lockfile && corepack pnpm test && corepack pnpm demo`.

The protocol's classical signature is ADR-36 secp256k1. The ML-DSA-87 signature is over UTF-8 `qorechain-msg-v1|<chain_id>|` concatenated with raw message bytes. Verification requires the classical signer address and the ML-DSA-87 public key registered for that address on chain (documented lookup `/qorechain/pqc/v1/account/{address}`). The tests verify the exact upstream test vector and negative cases. The demo supplies a local public test key instead of performing that registered-key lookup.

The mnemonic in `demo.mjs` is the public, unfunded BIP-39 test phrase. It is only for reproducible local tests. Never use it to secure funds. The sample instruction and recipient are synthetic; no network access, wallet account, registration, transaction, or agent-to-agent transport is used. This shows a protocol-compatible off-chain signature only. It does not establish that the QoreChain event's undefined “authenticated messaging” bounty requirement is fulfilled.

## Two-agent local message demo

`two_agent_demo.mjs` and `two_agent.mjs` model Agent A sending an explicit JSON message envelope to Agent B, then Agent B replying. Each envelope binds protocol/version, chain ID, message ID, sender, recipient, nonce, issue/expiry times, and body. Both directions use the official QoreSign v0.1.1 `signMessage` / `verifyMessage` API (ADR-36 secp256k1 + ML-DSA-87 hybrid signature). The receiving side checks its configured peer identity and recipient, chain, envelope schema, size and time bounds, verifies the signature, and then consumes a per-process nonce.

Run `corepack pnpm demo:agents` for the local round trip. Run `corepack pnpm test` for the QoreSign vector tests plus the two-agent tests: valid A→B and B→A messages, message/signature tampering, an untrusted signer, wrong recipient, expiry/future issue time, replay rejection, and schema/TTL limits.

The `two_agent_demo.mjs` variant is only an in-memory function handoff: it has no socket, broker, network transport, second process, key discovery, or live agent service. The trust store is preconfigured with two public BIP-39 test-vector identities; these published mnemonics are intentionally insecure and must never be used for funds. Replay state is a process-local `Set`, not durable or distributed. Expiry/replay checks are demo application logic, not chain enforcement. QoreSign signatures are protocol-compatible off-chain signatures, but the event's authenticated-messaging requirement is still undefined; this demo is not proof of live agent-to-agent messaging or bounty compliance.

## Separate-process loopback HTTP exercise

Run `corepack pnpm demo:agents:http` for two independent Node processes. Each process binds only `127.0.0.1`; Agent A sends a QoreSign-signed JSON envelope to Agent B over loopback HTTP, then B sends a signed reply to A. The receiver checks the configured test peer, recipient, chain ID, envelope fields, time bounds, signature and process-local replay set. The `http` integration test also exercises replay, tampering, a third untrusted test identity, and expiry across the local HTTP boundary. `corepack pnpm test` runs this with the in-memory protocol tests.

This socket is deliberately limited to loopback and test identities. It is not a public or production service: the processes use published insecure BIP-39 test vectors, a baked-in test trust mapping, volatile replay state, and no registered-key lookup. The local HTTP exchange is not QoreChain authenticated messaging, does not show a live agent service or on-chain enforcement, and does not establish the bounty requirement or compliance. No user key, wallet, account credential, chain-state write, or transaction broadcast is used.

Focused verification on 19 Nov 2026: all 13 QoreSign Node tests pass, including the loopback two-process integration test; `corepack pnpm demo:agents:http` confirms both message directions; the loopback worker and runner pass `node --check`.

## Signed proposal through the local BillGuard cap guard

The loopback HTTP receiver recognizes only the explicit `billguard.payment_proposal.local.v1` body as a payment proposal. After QoreSign verifies the signed envelope, it passes the proposal to `integration/local_proposal_guard.py`, which calls the existing `build_capped_plan` validator using receiver-side fixed demo values: one allowlisted target, one transaction per window, native `uqor`, 1,000,000 uqor window value, 800,000 uqor per-transaction cap, and 1,500,000 uqor daily cap. Sender-provided policy values are not accepted. The response distinguishes envelope authentication (`accepted`) from the policy decision (`payment_decision.accepted`); a valid signature does not make an out-of-policy payment acceptable.

Run `corepack pnpm demo:agents:http` to see a valid signed proposal accepted, a separately signed proposal with an out-of-scope target rejected, and a signed reply in the other direction. `corepack pnpm test` includes assertions for an accepted proposal, a forbidden recipient, transfer-plus-fee above the per-transaction cap, transfer-plus-fee above the EVM-window cap, plus the existing tampering, wrong signer, expiry, and replay failures.

This integration is a local simulation, not QoreChain or Diana enforcement. The windows/rules are hard-coded test fixtures, not queried from chain or loaded from a wallet. The plan is non-executable; no live signatures, wallet access, chain writes, transactions, or broadcasts occur. It uses only published insecure test identities. It is not proof that the bounty's authenticated-messaging criterion is met.
