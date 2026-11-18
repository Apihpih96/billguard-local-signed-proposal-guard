# BillGuard — QoreChain agent policy lab

BillGuard is a local prototype for a one-recipient bill-paying agent. The browser demo and Python policy model simulate authentication, replay, block-window, target, transaction-count, and value-plus-fee checks. They do not sign or send transactions.

## Project status, license, and attribution

This public repository contains an open-source local prototype; it is not a contest submission. The current demo is offline/local and does not sign or send transactions to QoreChain.

The original BillGuard project code is offered under the MIT License in `LICENSE` (copyright notice: 2026 Apihpih96). The project uses the external `@qorechain/qoresign` v0.1.1 package and includes its official test vector; QoreSign is under Apache License 2.0. See `THIRD_PARTY_NOTICES.md` and the included upstream license copy. Other packages are resolved from the checked-in lockfiles or requirements and retain their respective upstream licenses.

The review assets are in `assets/`: a cover concept and a 30-second text-led explainer. The explainer is not a screen recording or evidence of live-chain execution.

## Run locally

- Open `index.html` in a browser; it has no build step or network dependency.
- Install the test dependency in an isolated virtual environment, then run tests:
  `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements.txt`
  `python -m unittest discover -s tests -v`.
- Optional public-chain read-only environment preflight: `python3 integration/preflight.py`.
- Print a blank, owner-reviewable integration plan: `python3 integration/prepare_plan.py`.

The preflight performs only HTTP GETs against public QoreChain Diana REST endpoints. It reports network-wide abstract-account configuration, EVM permission availability, and the current EVM gas ceiling. A green result does not establish that any particular account has a registered key, funds, a linked authenticator, an active spending rule, or an open EVM window. A failed HTTP read is inconclusive. Neither script signs, broadcasts, registers keys, opens windows, or changes chain state. The plan contains placeholders and is not an executable transaction.

## Verified QoreChain path and safe scope

Official docs checked 12 Nov 2026 identify testnet `qorechain-diana` (EVM chain ID `9800`), REST `https://api-testnet.qore.host`, and EVM RPC `https://evm-testnet.qore.host`. The testnet ran node v3.2.8 from 12 Nov. Read-only endpoint checks in this package's preparation returned HTTP 200 at block height 9,952,888: abstract accounts enabled (`max_spending_rules: 5`), `evm` present in the permission schema, and an EVM transaction gas cap of 30,000,000. Re-run the preflight before relying on live state.

The published Post-Quantum AI Agents bounty calls for a scoped EVM window, transaction/value/duration/target bounds, smart-account spending rules, and authenticated messaging. It does not define what “authenticated messaging” means, so eligibility for that criterion still needs organizer confirmation.

Two documented building blocks are relevant, but they are distinct:

1. The EVM window requires the account's ML-DSA-87 key registered and a live window. On testnet, the EVM sender must use `eth_secp256k1`. Opening a window is a hybrid-signed Cosmos-lane action that the owner must authorize. The window's required bounds are blocks, max transaction count, and max value (native QOR value plus max fee). `nativeOnly` / `allowedTargets` further scope the target. This window does not cap arbitrary token-contract arguments; avoid routers and do not imply it caps token amounts.
2. A linked EVM authenticator can sign a chain-bound execution digest while an outer relayer submits and pays for the hybrid-signed Cosmos transaction. The account owner must authorize linking with a possession proof and spending-rule setup. A useful rule must be enabled with nonzero per-transaction and daily limits and allowed denominations; `uqor` is the native denomination. Authenticator sequence/nonce is distinct from the EVM account nonce. The adapter page says no authenticator nonce query is exposed there; current Rust SDK docs document `fetch_auth_nonce` for testnet v3.2.4+, so a concrete client path must be verified before implementation.

The candidate BillGuard design is a single fixed-recipient QOR payment with owner-approved short expiry, one transaction, a low explicit value/fee cap, and an enabled smart-account rule. The exact caps and recipient are intentionally unset for owner review. It should demonstrate both controls only after the actual testnet flow is verified. The initial simulation's boolean “authenticated” field is not cryptographic authentication or authenticated messaging. A separate new demo below uses the official QoreSign library for protocol-compatible off-chain signatures; that alone still does not establish authenticated agent-to-agent messaging or satisfy the bounty.

## Implementation limits and next prerequisites

The current project adds a live read-only environment preflight and an owner-reviewable, non-executable plan template; it does not add chain signing, wallet integration, authenticator linking, spending-rule enforcement, a relayer, or a transaction. QoreChain's v0.6.0 wallet-adapter docs (published 12 Nov) state that the signing and QoreX snippets have not been run end-to-end. Do not claim a working QoreChain integration or bounty-ready demo yet.

For a controlled real test, the owner would need a funded QoreChain testnet account using the correct `eth_secp256k1` EVM identity, a registered ML-DSA-87 key, and explicit authorization for a bounded window and/or the linked-authenticator plus spending-rule setup. Any test payment is a public on-chain write and needs separate explicit approval. No secrets were requested or handled here; no registration, linking, or transaction was performed.

## Sources

- [Build Before Q-Day and bounty requirements](https://build.qorechain.io/)
- [Official EVM Development guide](https://docs.qorechain.io/developer-guide/evm-development/)
- [Official Wallet Adapter guide](https://docs.qorechain.io/developer-tools/wallet-adapter/)
- [QoreChain SDK authenticated execution / nonce helpers](https://docs.rs/qorechain-sdk/latest/qorechain/authenticator/index.html)
- [QoreChain SDK SpendingRule reference](https://docs.rs/qorechain-sdk/latest/qorechain/proto/qorechain/abstractaccount/v1/struct.SpendingRule.html)

Recheck docs, network state and event rules before implementation or submission; they may change. Registration or submission has not been performed.

## Local signed-message verification (new)

Create and activate a virtual environment with `python3 -m venv .venv && . .venv/bin/activate`, install `python -m pip install -r requirements.txt`, then run `python integration/run_signed_demo.py` and `python -m unittest discover -s tests -v`. The demo creates a fresh, ephemeral Ed25519 key in process memory and verifies an instruction bound to the `billguard.qorechain.test` domain and QoreChain Diana EVM chain ID `9800`. It checks the signer fingerprint, signed payload, action/recipient shape, nonce replay, issue/expiry times and context before passing the request to the existing local policy simulator. The demo emits no key and makes no network write.

This makes the instruction-authentication step real cryptographic verification for a local test key, not the earlier boolean `sender_authenticated` shortcut. It is still not connected to a QoreChain account or linked authenticator; the local replay set is in-memory, and the simulated policy is not an on-chain rule. Ed25519 is classical, not post-quantum. It therefore does not establish compliance with the event’s authenticated-messaging criterion or provide post-quantum authentication. No owner key or secret was used.

The event brief names “authenticated messaging” but does not define its protocol, trust model or required proof. A useful question for the organizer is: “For the Post-Quantum AI Agents bounty, what does ‘authenticated messaging’ specifically require—signed agent instructions, authenticated agent-to-agent messages, or another protocol—and what proof should submissions provide?” A clarification email was sent on 13 Nov 2026; an exact-subject mailbox check on 19 Nov found only that outgoing message, with no reply.

The current official adapter documentation gives a QoreX interactive signing path and testnet endpoint, but explicitly says it has no tested quickstart and the signing/QoreX examples were not run end-to-end. The documented adapter also refuses to create/register keys, open an EVM window, or configure account-authority messages from a web request; those remain owner-authorized wallet actions. A safe, fully validated end-to-end test path is therefore not established by the docs or this local work. It would require a separate throwaway funded testnet account, its registered ML-DSA-87 key, a correctly configured EVM identity/window or linked authenticator and spending rule, and owner review of any on-chain setup/payment. This package has not performed those steps.


## Earlier experimental ML-DSA-87 harness

`pqcrypto==1.0.0` supplies a FIPS 204 ML-DSA-87 implementation. With the virtual environment active, run `python integration/run_mldsa_demo.py` for one local sign/verify round trip, then `python -m unittest discover -s tests -v`. This generates a fresh random throwaway keypair in process memory; the demo prints no key material and makes no network request or write. The tests exercise a valid signed instruction, payload/signature tampering, duplicate nonce replay, expiry, and mismatched sender/domain/chain.

This earlier Python harness proves only that the isolated local harness uses the ML-DSA-87 primitive to authenticate its own canonical JSON instruction format. That format and its `mldsa87:<SHA-256 public-key fingerprint>` sender identifier are experimental application-level choices; they are not a QoreChain account address, a QoreChain-native signature envelope, or a compatible wallet transaction. It is distinct from the official-library QoreSign off-chain message demonstration below. The key is generated randomly here, not with QoreChain's documented address-bound SHAKE-256 mnemonic derivation. The code does not produce the QoreChain `/qorechain.pqc.v1.PQCHybridSignature` extension, perform the outer secp256k1 wallet signature, register a key, open an EVM window, enforce chain state, or broadcast. In-memory nonce storage is only for tests and is not durable or atomic.

Official documentation describes QoreChain's ML-DSA-87 key material and hybrid Cosmos signing path, but the wallet-adapter signing examples are not documented as end-to-end tested; it does not establish that this standalone message format satisfies the bounty's undefined “authenticated messaging” criterion. Do not present this harness as a QoreChain integration or a bounty-compliant end-to-end demo.

The next prerequisite for real testnet enforcement is an owner-authorized disposable QoreChain testnet account with a registered ML-DSA-87 key and a correctly scoped EVM window or linked authenticator plus spending rules. Then the QoreChain-compatible signing/submission flow must be implemented and verified; any account setup or on-chain test transaction needs its own explicit approval. The event's authenticated-messaging requirement still needs organizer clarification. No account was inspected or modified, and no key was registered or transaction sent in this local work.

## Official QoreSign off-chain instruction signing (new)

`qoresign_demo/` uses the official `@qorechain/qoresign` TypeScript package pinned to v0.1.1 (upstream tag `go/v0.1.1`, commit `be7b85ac1b8be0cfc5fabf2cc7bd40bd43141f6c`) and the upstream `spec/message-signing-v1.md`. From that directory, run `corepack pnpm install --frozen-lockfile`, `corepack pnpm test`, and `corepack pnpm demo` (Node.js 20+). The demo signs a synthetic local BillGuard instruction via QoreSign's ADR-36 secp256k1 plus ML-DSA-87 hybrid `signMessage` API, then verifies via the official `verifyMessage` API. The tests include the upstream v0.1.1 published message-signing vector and reject changed message, chain ID, or PQ key. The PQ signature domain is UTF-8 `qorechain-msg-v1|<chain_id>|` followed by the raw message bytes.

A real verifier must obtain and authenticate the signer's registered PQ public key on chain (the documented lookup is `/qorechain/pqc/v1/account/{address}`); this demo deliberately does not perform that lookup. It uses a public, unfunded BIP-39 test mnemonic and a synthetic recipient only, and makes no network request. Therefore this establishes a local protocol-compatible off-chain signature/verification example, not a signature by an owner account, chain transaction, or account registration. The separate local-loopback proposal demo described below is still not a live agent service or proof of the bounty criterion. Whether this qualifies for the bounty's separately stated “authenticated messaging” requirement remains undefined and unconfirmed; do not claim bounty eligibility or submit it as proof of live messaging.

## Offline capped-payment validation (new)

Run `python integration/run_capped_demo.py` for a deterministic, entirely synthetic native-QOR payment plan. It checks a one-transaction EVM window, one fixed recipient, native-only/no-calldata behavior, amount plus maximum fee against the window cap, and separate abstract-account per-transaction and daily caps. Values and addresses in this fixture are fake examples; they are not Apih's account, a quote, or a proposed live payment. Run `python -m unittest discover -s tests -v` for all regression tests.

`integration/capped_payment.py` only validates local inputs and emits a non-executable JSON plan. It has no network or wallet code. It never signs, opens a window, broadcasts, or changes chain state. Its cap arithmetic is a conservative local simulation, not evidence that any on-chain spending rule/window exists or that the chain enforces these checks. No live EVM sender, recipient, amount, or fee has been selected. A live test transaction requires an exact review with those terms; any owner-signed window or rule setup also needs separate approval.

## Official EVM window reference and local proofs (checked 13 Nov 2026)

This addendum uses the current official [EVM Development guide](https://docs.qorechain.io/developer-guide/evm-development/) and [EVM Authorisation Window Reference v3.2.8](https://docs.qorechain.io/developer-guide/evm-window-reference/). Diana is documented as running v3.2.8; the guide describes the v3.2.8 scope additions as testnet-only until a later mainnet upgrade.

The documented native EVM authorisation window requires `blocks` 1–17,280, `max_txs` 1–1,000, and positive `max_value` in `uqor`. `blocks` counts from the opening block, not wall-clock time. At admission each EVM transaction consumes one transaction slot and reserves its transferred native value plus `gas limit × fee cap`; that sum converts from 18-decimal wei to 6-decimal `uqor` rounding up. An admitted transaction that later reverts still consumes its slot and value allowance. Token amounts are not priced/capped by `max_value`: a token call carries zero native value, so its maximum gas fee is the window charge; a listed contract may move token amounts according to its own code and existing approvals.

On the documented v3.2.8 testnet, optional `allowed_targets` accepts up to 16 unique 20-byte `0x` recipients and refuses contract creation; `native_only` allows plain QOR transfers only (no calldata, contract creation, code recipient, or EIP-7702 authorization). These scope options are not documented as available on the current mainnet version. The reference also says EVM windows do not charge the account's own top-level Native-lane messages or abstract-account executions authorized by authenticators. It lists Native-lane bank sends, staking, governance, and self-signed `MsgCrossVMCall` as out of scope, and module-run ERC-20 conversions/IBC callbacks. Important distinction: an EVM-lane cross-VM call under an authz grant and certain delegated EIP-7702 actions can still require a live window; this is not a blanket rule for every transaction involving a module.

### Runnable local verification

Install an isolated environment and run:

```sh
uv run --python 3.12 --no-project --with-requirements evm_proof/requirements.txt pytest -q evm_proof
```

`evm_proof/window_model.py` is an offline explanatory model of the documented window admission limits, gas-reserve arithmetic, block boundary, reverted-admission accounting, target list, `native_only`, and the stated Native/abstract-account exclusions. `evm_proof/ScopedSpendGuard.vy` is a separate simple local EVM contract demonstrating app-level agent-only execution to one fixed native recipient with a transaction count, per-call value, cumulative native amount and block expiry. Its tests use PyEVM only; no QoreChain node is contacted.

Neither artifact implements QoreChain's `MsgOpenEVMWindow`, its protocol admission/settlement hooks, ML-DSA hybrid authorization, or QoreChain abstract-account spending rules. The Vyper guard counts only successful contract executions (failed/reverted calls roll back state), and its `max_total` tracks native transfer amounts only—not gas fees or protocol settlement charges. Therefore use `window_model.py` for the documented protocol accounting model and describe the Vyper guard only as a local smart-contract policy illustration. Neither has been deployed or tested on Diana.

### Authenticated messaging: documented requirement, no defined interface

The event page's Post-Quantum AI Agents bounty requirement is exactly “Scoped EVM window; transaction, value, duration and target limits; smart-account spending rules; authenticated messaging.” The EVM Development and EVM Window Reference pages above do not define an authenticated-messaging protocol, message schema, authentication/trust model, API, or required evidence. The QoreSign specification defines off-chain account message signatures, but not an agent-to-agent transport or the bounty's proof criteria; it cannot resolve whether that suffices. The requirement therefore remains an organizer clarification / implementation dependency; this package does not claim it is met.

All browser simulations, cryptographic harnesses and EVM tests in this package remain local. No QoreX use, account changes, wallet import, key registration, window opening, deployment, chain transaction, or contest submission was performed. This source repository is public; no contest entry has been submitted.

## Defensive input validation note

The local policy simulator now requires the explicit Boolean `True` for its demo authentication flag; truthy strings such as `"false"` are rejected. The EVM documentation model also rejects Boolean/fractional values for integer block, wei, gas, and uqor inputs to prevent float accounting. These are local input checks, not real cryptographic authentication or on-chain enforcement. See `VALIDATION.md` for reproductions and current test totals.

## Read-only Diana account readiness inspector (new)

Use `python3 integration/testnet_readiness.py --account qor1…` with the public canonical account address. It uses only anonymous HTTPS GETs to the fixed Diana REST host; it accepts no keys, passwords, or transaction data. It reads the public environment config/permission/gas endpoints, then the documented account PQC status, EVM-window status, linked authenticators, and spending rules. It reports unknown for missing/malformed fields and never signs, broadcasts, registers, opens/closes a window, or changes chain state.

The readiness check is intentionally preliminary: it checks a PQC key status and the EVM window’s explicit `live` field, active non-revoked unexpired authenticators with `evm` permission, and a narrowly recognized positive native-`uqor` per-transaction/daily spending rule. It does not prove the user’s `eth_secp256k1` key/address is the one tied to the `qor1` account, inspect its funds, validate a proposed target’s effects, or establish the bounty’s authenticated-messaging requirement. A found window may not be safe for this payment; always inspect its exact target/scope and current remaining bounds. A high-level `requires_manual_review` is not execution approval.

A fresh environment preflight attempt on 19 Nov 2026 received HTTP 403 for all three public environment reads. That response is inconclusive and does not establish missing Diana configuration or a chain outage. No account-specific address was queried in this preparation.

## Diana spending-rule constraint correction (checked 19 Nov 2026)

The current SDK `SpendingRule` reference describes EVM outflow measurement from chain v3.2.2: native value/balance decrease, bank coins spent, and the balance or allowance change of each listed ERC-20 are included in rule accounting. That is separate from the EVM window's `max_value`, which still does not cap arbitrary token-contract arguments. An allowlisted EVM target trusts its arguments, recipient included; ERC-721/ERC-1155 transfers through allowed contracts are not capped by these rules. Empty `allowed_denoms` means any denomination, so a least-privilege rule should explicitly restrict denoms and use positive per-transaction and daily limits. The local readiness inspector does not claim these on-chain checks have been enabled or exercised.

## QoreX owner-reviewed native payment scaffold (new, 19 Nov 2026)

`integration/qorex_payment_demo/` is a browser integration scaffold based on the official `@qorechain/wallet-adapter` 0.6.0 page. It builds a standard native Diana `MsgSend` from owner-entered addresses and integer `uqor`, shows the exact transfer before a distinct button, then calls the documented QoreX adapter only from that explicit click. QoreX remains the signer and the wallet's own approval is required before its signing/broadcast. It asks for no mnemonic, private key, PQC secret, or recovery code; it never auto-switches networks. See the subdirectory README for setup and limitations.

The pure request-module tests run without a wallet or network: `cd integration/qorex_payment_demo && npm test`; JavaScript syntax can be checked with `node --check src/payment_core.mjs` and `node --check src/main.js`. The scaffold itself and the official adapter's QoreX signing flow have not been run end-to-end. This is only a user-authorized transfer integration; it does not make BillGuard's simulated caps enforceable, configure a linked authenticator or EVM window, or prove authenticated agent messaging. No transfer was requested or performed.

The readiness inspector's earlier HTTP 403 responses remain inconclusive; this work did not retry through another route. To deliberately exercise the UI, the owner needs QoreX installed and already set to Diana, plus a disposable funded testnet account. A true bounded-agent test still needs separate owner-authorized setup of a registered PQC key and the appropriate scoped window/authenticator and spending rule, followed by an explicitly approved test transaction. Do not use the user's ordinary wallet for this scaffold.


## Official QoreX setup path and hard limits (checked 19 Nov 2026)

The QoreX EVM-window reference now documents a native owner-operated route for a basic EVM window: in the mobile app, Settings → Security → EVM access window; in the browser extension, use the EVM access window button in its popup. It applies to an Ethereum-style coin-60 account, not the default Cosmos coin-118 account. QoreX asks the owner to approve a hybrid-signed `MsgOpenEVMWindow`. The three required bounds are blocks, transaction count, and a QOR cap that includes each transaction's maximum fee; documented defaults are 300 blocks, 5 transactions, and 1 QOR. Opening replaces an existing window and advances the account nonce. This is a wallet UI path, not a callable setup API for this demo.

The QoreX window card does not expose `native_only` or `allowed_targets`; the docs say those scope fields require `qorechaind` or an SDK path. The official wallet-adapter refuses `MsgOpenEVMWindow` as well as `MsgRegisterAuthenticator`, `MsgRevokeAuthenticator`, and `MsgUpdateSpendingRules` in `qorexSignAndBroadcast`, including when nested in `MsgExec`. The existing browser scaffold therefore cannot use its transfer button to configure any of them.

QoreX docs say linked Phantom/MetaMask signers with spending limits are not available inside QoreX yet. The Dashboard's Keplr-linked Phantom route is not a QoreX setup route. The official Account Abstraction guide now documents Diana CLI commands for replacing rules and registering an authenticator with a possession proof; these actions require the owner's root signature and fee, and the external key's proof. The SDK also has composition/proof helpers, but QoreX `qorexSignAndBroadcast` refuses account-authority messages. The command shapes and unexecuted steps are documented in `DIANA_OWNER_RUNBOOK.md`; no account setup was run here.

**Updated conclusion (19 Nov 2026):** the official docs now provide a `qorechaind` generate-only + PQC-cosign route for scoped Diana EVM windows, and a Diana-only CLI/SDK route for smart-account spending rules and linked authenticators. The package did not run any of those setup commands or alter chain state. The exact owner-only steps, prerequisites, placeholders, and boundaries are in [`DIANA_OWNER_RUNBOOK.md`](DIANA_OWNER_RUNBOOK.md). A prepared transfer scaffold or local tests still do not prove live spending-rule enforcement or authenticated agent messaging.


## Owner-only Diana setup reference (19 Nov 2026)

See [`DIANA_OWNER_RUNBOOK.md`](DIANA_OWNER_RUNBOOK.md) for the official command shapes for the registered ML-DSA-87 prerequisite, scoped EVM windows, linked-key possession proof, spending-rule replacement, and the separate owner signing/broadcast steps. It is a runbook only: no account details or signatures are included, and no commands were run against Diana. The bounty's messaging proof criterion remains undefined; see the runbook for the latest reply check.

## Two-agent authenticated-message exercise (local only)

The QoreSign subproject now includes `two_agent.mjs`, `two_agent_demo.mjs`, and adversarial tests. Two test identities exchange explicit envelopes containing a protocol version, chain, sender/recipient, unique message ID and nonce, issue/expiry times, and message body. Each side verifies the other side's QoreSign v0.1.1 ADR-36 secp256k1 + ML-DSA-87 hybrid signature using a preconfigured test public key; tests cover both directions, tampering, wrong signer/recipient, expiry, future issue time, replay, invalid schema, and TTL/body bounds. Run `cd qoresign_demo && corepack pnpm demo:agents && corepack pnpm test`.

This uses only an in-memory function handoff between two simulated agents, not a network transport or live agent service. The public BIP-39 test-vector keys are insecure and must never secure funds; no account key or chain registration lookup is used. The replay cache is an in-memory Set and the expiry/replay logic is app-level only. Therefore it demonstrates local message signing and verification, not live agent-to-agent messaging, on-chain enforcement, or proven compliance with the bounty's undefined authenticated-messaging criterion. No credentials, wallet, addresses, or broadcasts are involved.

### Separate-process local HTTP message exercise (19 Nov 2026)

The QoreSign demo now also includes `loopback_agent.mjs`, `two_agent_http_demo.mjs`, and `test/two_agent_http.test.mjs`. Run `cd qoresign_demo && corepack pnpm install --frozen-lockfile && corepack pnpm demo:agents:http && corepack pnpm test`. Two separate Node processes bind only to `127.0.0.1` and exchange signed envelopes over loopback HTTP. Integration tests retain the prior in-memory checks and also exercise two-way process exchange, tampering, wrong signer, expiry and replay across the HTTP receiver.

This remains a local exercise with public insecure BIP-39 test-vector identities and a test-only preconfigured trust map; replay state is process-local. It does not perform registered-key lookup, use user credentials or wallet keys, modify chain state, broadcast a transaction, or provide a public/production network service. Local HTTP transport plus protocol-compatible signatures is not proof of QoreChain authenticated messaging or bounty compliance; organizer clarification remains necessary.

Focused verification for the separate-process exercise: all 13 QoreSign Node tests pass; the demo reports both loopback directions accepted; worker and runner pass `node --check`. The broader Python/EVM suites were not rerun for this JavaScript-only update.

## Local signed proposal + policy-guard integration (new)

The separate-process QoreSign loopback demo now passes a signed payment proposal from Agent A to Agent B. After checking the message signature, peer identity, chain label, nonce, and expiry, the receiver validates the proposal with the existing Python `build_capped_plan` guard using fixed receiver-side local test caps. The sender cannot choose or relax those caps. An accepted signature and a rejected payment are represented separately. The demo verifies a bounded proposal and rejection for an unallowlisted recipient; integration tests also reject total amount-plus-fee above the per-transaction and EVM-window caps, and retain replay/expiry/tamper/wrong-signer checks.

Run from `qoresign_demo/`: `corepack pnpm install --frozen-lockfile && corepack pnpm test && corepack pnpm demo:agents:http`. The proposal passes only local fixture values (single target, native `uqor`, 1,000,000 uqor simulated window, 800,000 uqor per-transaction, 1,500,000 uqor daily). These are not account state or deployed chain rules. This remains local simulation—not on-chain enforcement, live QoreChain authenticated messaging, or proof of bounty compliance. It uses public insecure test keys and no user credentials/wallet, networked writes, signing with user keys, or broadcasts.

### End-to-end local proposal rejection checks (19 Nov 2026)

The separate-process HTTP integration test now asserts the complete proposal path: a 700,000 uqor amount plus 50,000 uqor maximum fee passes the fixed local caps and returns a non-executable plan requiring owner review; an unallowlisted recipient, an amount exceeding the local per-transaction cap, and an amount-plus-fee exceeding the local EVM-window value cap each return a policy rejection without a plan. Tampered, replayed, expired, and untrusted-signer envelopes are rejected by the receiver before it returns a payment-policy decision. Tests assert rejected proposals/envelopes expose no approval or execution fields. The receiver has no approval, signing, or execution mechanism at all; this test verifies only that it stops at the policy decision boundary.

Verification: `cd qoresign_demo && corepack pnpm test` passes 13 Node tests, `corepack pnpm demo:agents:http` completes the two-process demo, `node --check` passes for the worker, runner, and HTTP test, and `python3 -m unittest discover -s tests -p 'test_capped_payment.py' -v` passes all 9 focused Python cap-guard tests. Everything uses public test-vector identities and fixed local caps. No user keys, wallet, credentials, chain writes, or broadcasts are used. These results do not establish live QoreChain authentication, chain-enforced spending limits, or bounty compliance; organizer clarification and owner-authorized live setup/testing remain outstanding.
