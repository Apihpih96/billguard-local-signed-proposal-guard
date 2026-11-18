# QoreChain BillGuard prototype — verification note

Checked: 2026-11-13 15:46 UTC (23:46 MYT)

## What is in this package

BillGuard is a local, single-recipient capped-payment agent prototype. It combines a browser demo, deterministic policy checks, a local signed-instruction verifier, an experimental FIPS 204 ML-DSA-87 message-signature harness, an official-library QoreSign v0.1.1 off-chain hybrid message-signing demonstration, a synthetic capped-payment plan, and a read-only Diana testnet preflight.

## Verification completed

- Python unit suite: 41 tests passed (`uv run --no-project --with 'cryptography>=44,<47' --with 'pqcrypto==1.0.0' python -m unittest discover -s tests -v`).
- ML-DSA-87: local ephemeral-key instruction sign/verify round trip passed.
- Capped-payment: synthetic plan passed the local one-recipient/native-transfer, transaction-count, value-plus-fee and spending-rule arithmetic checks; output is explicitly non-executable.
- Signed instruction: local Ed25519 sign/verify round trip passed; Ed25519 is classical, not post-quantum.
- Browser-demo inline JavaScript: `node --check` passed.
- Read-only Diana environment preflight: HTTP reads reported abstract accounts enabled, maximum 5 spending rules, EVM permission present, transaction gas ceiling 30,000,000 and precompile input maximum 16,384 bytes. Environment-wide checks passed on 2026-11-13 15:28:35 UTC.

## Important boundary

This is not a live QoreChain agent integration or submission-ready demo. It has not used an owner account, registered a key, linked an authenticator, set a chain spending rule, opened an EVM window, signed a QoreChain transaction, or broadcast a transaction. The environment preflight does not establish account readiness or on-chain enforcement. The earlier Python ML-DSA message format is experimental. Separately, the new TypeScript demo uses the official QoreSign v0.1.1 off-chain ADR-36 + ML-DSA-87 signing/verification API and verifies an upstream published vector; it does not fetch a signer's registered on-chain PQ key, connect an agent to another agent, or prove the event's undefined authenticated-messaging criterion. The existing QOR transfer to the main wallet is a separate basic transfer test and does not prove this agent's limits or authenticated messaging.

No registration, publication, repository push, or contest submission was performed.

## Next gates before a truthful submission

1. Confirm the organizer's exact authenticated-messaging evidence requirement.
2. Implement and test the native QoreChain signing/authorization integration, not a local-only substitute.
3. On a disposable testnet account, verify the registered key, restricted EVM window and/or linked authenticator plus chain spending rule, and demonstrate an allowed action and rejected out-of-policy actions. Owner-authorized setup and any test transaction require separate review.
4. Refresh official rules and prepare a demo/evidence; submit only after Apih's explicit approval.

## Official EVM window documentation and local tests (supplement, 2026-11-13)

Sources reread: [EVM Development](https://docs.qorechain.io/developer-guide/evm-development/), [EVM Authorisation Window Reference v3.2.8](https://docs.qorechain.io/developer-guide/evm-window-reference/), and [Build Before Q-Day bounty table](https://build.qorechain.io/).

- Re-ran the original Python unit suite: all 41 tests passed again.
- Local PyEVM/Vyper and documentation-model suite: 19 tests passed with `uv run --python 3.12 --no-project --with-requirements evm_proof/requirements.txt pytest -q evm_proof`.
- The tests cover documented block (1–17,280) and transaction (1–1,000) bounds; the opening-height block boundary; positive `uqor` value cap; native transfer plus `gas limit × fee cap` rounded up to `uqor`; admitted/reverted transaction accounting; optional max-16 unique target list and contract-creation rejection; `native_only` conditions; token-call value accounting; and the stated exclusion of own Native-lane messages / authenticator-authorized abstract-account executions. The Python model does not emulate the documented post-execution settlement charge for native QOR moved by an EVM precompile.
- A separate Vyper contract was compiled and executed in the local PyEVM test harness to demonstrate a fixed-recipient, agent-only cap/count/expiry policy. It is not the QoreChain window implementation or an abstract-account authenticator. Its counters roll back on reverted calls and its amount ceiling ignores gas, unlike QoreChain's documented admission/settlement accounting; the Python model holds the protocol accounting rules separately.
- The bounty page states “authenticated messaging” but neither requested EVM page defines a protocol, schema, trust model, API or proof criteria for it. EVM authorization and abstract-account authenticator details do not establish that criterion. Organizer clarification is still needed.

No QoreX or wallet access, wallet import/deletion, key/window/rule configuration, deployment, live transaction, publication or submission took place in this update. All newly added execution remains local/simulated.

## Official QoreSign off-chain message demo (supplement, 2026-11-13)

- Upstream source: [qorechain/qoresign tag go/v0.1.1](https://github.com/qorechain/qoresign/tree/go/v0.1.1), commit `be7b85ac1b8be0cfc5fabf2cc7bd40bd43141f6c`, spec `spec/message-signing-v1.md`; npm dependency is pinned to `@qorechain/qoresign` 0.1.1.
- The official API produced a hybrid signature (`ml-dsa-87-hybrid`, algorithm id 1) and verified the synthetic sample instruction offline. It signs the classical ADR-36 secp256k1 message form and the ML-DSA-87 bytes `UTF-8("qorechain-msg-v1|" + chain_id + "|") || raw UTF-8 message`.
- Tests: five new Node tests passed, including upstream's published message-signing vector; valid signature verification; tampered-message / wrong-chain rejection; different/missing PQ key rejection; and exact domain-prefix bytes.
- Reproduce with Node.js 20+: `cd qoresign_demo && corepack pnpm install --frozen-lockfile && corepack pnpm test && corepack pnpm demo`.
- The demonstration uses the public, unfunded BIP-39 test mnemonic and synthetic values, with no network calls. It does not query `/qorechain/pqc/v1/account/{address}` for a registered PQ key; that lookup is a verifier requirement in production. Thus this confirms use of the official off-chain signature format only—not a live account signature, authenticated agent-to-agent protocol, bounty eligibility, or a completed on-chain agent.
- Re-ran the existing suites with this update: original Python suite 41 passed; EVM documentation-model / PyEVM suite 19 passed; QoreSign suite 5 passed. No wallet use, account changes, chain write, deployment, publication or submission occurred.

## Defensive input audit and fixes (2026-11-13)

A reproducible review found two fail-open input-validation defects in the local simulators:

- `policy_engine.evaluate` treated any truthy value as `sender_authenticated`; for example, the string `"false"` was admitted as authenticated. It now requires the exact Boolean `True` and rejects malformed auth, nonce, target, numeric, policy, and state values without consuming simulated state. This remains a demo flag, not cryptographic authentication.
- `evm_proof.window_model` accepted booleans and fractional numeric values for integer block/wei/uqor inputs; e.g. a fractional wei charge could return a floating-point uqor value. It now enforces nonnegative or positive exact integers (excluding `bool`), validates typed flags/calldata, and rejects malformed initial counters.

Regression checks reproduce both cases and verify rejection without state mutation. Current full rerun: Python 43 tests passed; EVM/PyEVM suite 21 passed (one upstream `websockets.legacy` deprecation warning); official QoreSign suite 5 passed; demo completed and reported local verification; browser-demo inline JavaScript syntax check passed.

These fixes harden local input validation only. They do not add live signing, registered-key lookup, QoreChain enforcement, an agent-to-agent transport, or evidence that the bounty's authenticated-messaging criterion is met. No wallet or chain account was used or changed, and nothing was deployed, published, or submitted.

## Second independent audit (2026-11-14)

The read-only environment preflight had another fail-open parser: it accepted JSON boolean `true` as a positive gas limit (because Python converts it to integer 1), accepted malformed permissions such as the string `"evm"` as containing the EVM permission, and used permissive integer coercion. It now accepts only positive integers or digit-only decimal strings for gas limits, requires a list of string permissions, checks nested response shapes defensively, and treats malformed top-level REST JSON as an inconclusive read error. Regression tests cover the reproductions and verify the readiness result fails closed. No live endpoint or account was queried during this audit; the change only hardens local parsing.


## Third audit (2026-11-14)

A further edge-case pass found and fixed three local robustness/correctness issues:

- Preflight gas parsing now fails closed on an extremely long digit string instead of raising Python's integer-conversion `ValueError`.
- EVM target validation now requires ASCII hexadecimal digits; Python's integer parser had accepted Unicode decimal digits as address characters.
- EVM transaction accounting now rejects a zero gas limit, which cannot describe a valid EVM transaction. Synthetic fixtures use a positive gas limit.

New regression tests cover all three cases. Full local rerun: Python 47 passed; EVM/PyEVM 23 passed; QoreSign 5 passed; local signing and browser syntax checks passed. These remain offline models and do not demonstrate live QoreChain controls or authenticated agent messaging. No wallet, chain, deployment, publication, or submission was involved.

## Fourth independent audit and follow-up (2026-11-14)

A fresh malformed-input review found that deeply nested JSON-compatible payload values could make canonical JSON serialization raise an uncaught `RecursionError` in both the Ed25519 and ML-DSA instruction verifiers. This did not authenticate an invalid instruction, but it escaped the verifier's typed rejection path and could interrupt a caller. Both verifiers now convert that failure into their normal signature-verification error; regression tests exercise the deeply nested payload. The same pass added strict checks for verifier context types and nonce-store mutability, plus preflight tests that malformed UTF-8 or excessively nested REST JSON becomes an explicit read error rather than an uncaught crash.

Follow-up audit rechecked the affected verifier and preflight paths, confirmed the new regression cases reject the malformed inputs, and found no further reproducible defect in the inspected scope. This is not exhaustive proof.

Fresh local verification after the fixes: 56 Python tests passed; 23 EVM/PyEVM tests passed (one upstream `websockets.legacy` deprecation warning); 5 official QoreSign Node tests passed. Capped-payment, Ed25519, ML-DSA and QoreSign demos completed; the inline browser-demo JavaScript passed `node --check`. No live wallet/chain operations, publication, deployment or submission occurred. The work remains offline/simulated and does not demonstrate live QoreChain enforcement or authenticated agent-to-agent messaging.

## Read-only account inspector and latest safe-path work (2026-11-19)

Added `integration/testnet_readiness.py` and regression coverage. It composes the documented Diana reads for environment settings, `GET /qorechain/pqc/v1/account/{qor1}`, `GET /qorechain/pqc/v1/evm_window/{qor1}`, and account `authenticators` / `spending_rules`. These routes are based on the official QoreChain EVM guide and SDK source. A QoreChain EVM window is explicitly reported using the chain's `found`, `live`, bounds/remaining values and target/native-only scope; a mere stored `found` window is not described as live. Public-key bytes are not printed. Malformed/unfetched fields stay unknown.

The tool validates the `qor1` path input, uses only anonymous HTTPS GETs to the fixed host, sets short time/response-size limits, refuses redirects to a different host, and has no signing/broadcast path. Rule recognition fails closed and only credits an enabled rule with positive per-tx and daily `uqor` caps and the appropriate EVM permission/key association; the documented first-enabled account-wide rule is not bypassed. It never chooses an address or imports owner secrets.

Fresh live public environment reads attempted during this update returned HTTP 403 on each of the three endpoints. This is an access/response outcome for those reads only: chain state and account readiness remain unknown. No account-specific address query was run. The account inspector is prepared for an authorized local run once REST reads are reachable, but this change does not make a live testnet transaction.

Official docs checked for the constraints: [EVM Development](https://docs.qorechain.io/developer-guide/evm-development/), [wallet adapter](https://docs.qorechain.io/developer-tools/wallet-adapter/), [SDK EVM-window source](https://docs.rs/qorechain-sdk/latest/src/qorechain/evm_window.rs.html), [SDK abstract-account REST source](https://docs.rs/qorechain-sdk/latest/src/qorechain/abstractaccount.rs.html), [SDK SpendingRule reference](https://docs.rs/qorechain-sdk/latest/qorechain/proto/qorechain/abstractaccount/v1/struct.SpendingRule.html), and [PQC account status docs](https://docs.qorechain.io/api-reference/json-rpc-qor_-namespace/). Documented guardrails include Diana chain id 9800; an ML-DSA-87-registered account and an open EVM authorization window for EVM-lane transactions; `eth_secp256k1` EVM identity; window bounds (1–17,280 blocks, 1–1,000 transactions, positive `uqor` value-plus-max-fee cap); and v3.2.8 testnet scopes (`native_only`, `allowed_targets`). The window and abstract-account spending rule are distinct controls.

Current tests after adding the inspector: 65 Python unit tests passed, including nine new inspector cases; a string-form Unix expiry regression is included. The EVM/PyEVM test suite could not be rerun because the shared Computer filesystem had only 44 MB free and `uv` could not extract pytest (`No space left on device`); this is a test-environment limitation, not a code-test failure. No EVM/PyEVM files were changed. The existing QoreSign demo passed `node --check`, but its test suite was not rerun; no EVM/PyEVM or QoreSign test results are claimed for this update. All prior project tests and demos remain local and are not evidence of live Diana enforcement.

## QoreX owner-reviewed payment scaffold (19 Nov 2026)

Focused checks for `integration/qorex_payment_demo/`: all 5 Node built-in tests pass, covering request construction, integer/address checks, mandatory owner-click gating, exact MsgSend fields, unavailable QoreX, and user-decline handling. `node --check` passes for both JavaScript modules. These tests use a stub wallet and encoder; they do not invoke QoreX, sign, broadcast, or contact Diana.

The full Python unittest suite was attempted but could not import two existing test modules in this environment because `pqcrypto` and `cryptography` are not installed; therefore it did not complete. This is an environment dependency limitation, not a passing full-suite result. No live testnet readiness or end-to-end wallet behavior is established.


## Diana CLI runbook documentation check (19 Nov 2026)

Added `DIANA_OWNER_RUNBOOK.md`, checked against the official EVM Window Reference, EVM Development, Post-Quantum Signing, Account Abstraction and Wallet Adapter pages. Static checks verified that the runbook has no concrete account or contract address, owner keys and linked-key proof are placeholders, and the generated window/rules/link files precede the owner-only `qorechaind tx pqc cosign` broadcasts. This validates document content only: no `qorechaind` binary was invoked, no account was selected, and no key, signature or transaction was created. The Account Abstraction guide says the CLI link-message / `--possession-proof` command shape is sourced from v3.2.8 node code and has not been run in the guide itself.

## Local two-agent QoreSign message exercise (19 Nov 2026)

Added `qoresign_demo/two_agent.mjs`, `two_agent_demo.mjs`, and `test/two_agent.test.mjs`. Validation performed locally: `corepack pnpm demo:agents` showed Agent A→B and B→A both verified; `corepack pnpm test` passed all 12 QoreSign Node tests; `node --check` passed for the new and existing QoreSign demo JavaScript files. The tests include body/signature tampering, wrong trusted signer, wrong recipient, expiration/future timestamps, replay, schema/chain/body/TTL guards.

Scope: in-memory handoff only; published BIP-39 test vectors; test public keys are locally preconfigured; nonce cache is an in-memory Set. No network, live agent transport, chain lookup, account, wallet, secret, signing key from the user, or broadcast was used. This is not proof of the event bounty's undefined authenticated-messaging requirement or live agent-to-agent messaging.

## Separate-process loopback HTTP QoreSign exercise (19 Nov 2026)

Added `qoresign_demo/loopback_agent.mjs`, `two_agent_http_demo.mjs`, and `test/two_agent_http.test.mjs`. The sender and receiver run as distinct Node processes, bind explicitly to IPv4 loopback (`127.0.0.1`), and exchange signed JSON envelopes via HTTP. The integration test checks successful A→B and B→A delivery, then rejects replayed and body-tampered envelopes, an envelope from an untrusted third test identity, and an expired envelope. Existing in-memory negative tests remain.

Reproduce with `cd qoresign_demo && corepack pnpm install --frozen-lockfile && corepack pnpm demo:agents:http && corepack pnpm test`. This is local-only test transport using public insecure BIP-39 test vectors and a fixed test trust map; the replay cache is in-process. It is not live QoreChain messaging, a public service, a registered-key verifier, on-chain enforcement, or proof of the bounty's undefined authenticated-messaging criterion. No user secrets, wallet or chain writes, signatures from the user's keys, or broadcasts were used.

Focused verification for this transport update: `corepack pnpm test` passed all 13 QoreSign tests (including the separate-process loopback integration test); `corepack pnpm demo:agents:http` confirmed both directions were accepted over `127.0.0.1`; `node --check` passed for the worker and demo runner. The package install used the existing local pnpm cache. The full Python/EVM suites were not rerun because this change only touched the QoreSign demo and its documentation.

## Local two-agent proposal guard integration

The HTTP two-process demo passes `billguard.payment_proposal.local.v1` only after the receiver verifies the QoreSign envelope, then runs it through `integration/local_proposal_guard.py` and the existing `build_capped_plan` policy. Tests verify a 700,000 uqor payment plus 50,000 uqor maximum fee is accepted by the fixed local fixture; recipient `0x3333333333333333333333333333333333333333` is rejected; amount plus fee above the simulated 800,000 per-transaction cap is rejected; and amount plus fee above the 1,000,000 window cap is rejected. Existing message tests still reject replay, expiry, body tampering, wrong signer/recipient, wrong chain, malformed schema and excessive TTL.

Verification on 19 Nov 2026: `pnpm test` passed 13 Node tests with 0 failures. `pnpm demo:agents:http` completed both message directions, accepted the signed payment proposal with simulated worst-case outflow 750,000 uqor, rejected the out-of-scope recipient, and reported `transaction_sent: false`. `node --check` passed for `loopback_agent.mjs` and `two_agent_http_demo.mjs`. These are local test-vector identities and fixed simulated caps only. The result demonstrates neither QoreChain account state nor deployed/on-chain enforcement, live agent messaging, nor bounty compliance.

## Proposal-to-guard end-to-end rejection assertions (19 Nov 2026)

Extended `qoresign_demo/test/two_agent_http.test.mjs` so the separate-process receiver is exercised through signature verification and BillGuard's fixed local Python cap guard. The successful 700,000 uqor + 50,000 uqor case returns a policy-admitted plan with `execution.executable=false`, signing/broadcast false, and exact owner review required. Invalid target, 900,000 + 50,000 above the 800,000 per-transaction cap, and 980,000 + 50,000 above the 1,000,000 EVM-window value cap all return a policy rejection without a plan. Tampered, replayed, expired, and wrong-signer envelopes return receiver errors before a payment-policy decision. Assertions ensure these rejection paths contain no approval or execution fields.

Focused verification: `corepack pnpm test` passed all 13 Node tests; `corepack pnpm demo:agents:http` completed both directions and reported a successful local policy plan plus rejection of the unauthorized target, with `transaction_sent: false`; `node --check` passed for the loopback worker, demo runner, and integration test; `python3 -m unittest discover -s tests -p 'test_capped_payment.py' -v` passed all 9 Python cap-guard tests. The receiver only validates and produces/rejects a local plan; no approval, signing, or execution code exists in it. These are local tests with public insecure test-vector keys and fixed fixture caps—not live chain proofs or verified Diana configuration. No wallet, user keys, credentials, chain writes, or broadcasts were used. Live setup/testing still requires owner-chosen settings and separate authorization; the bounty's authenticated-messaging criterion remains unclear pending organizer response.
