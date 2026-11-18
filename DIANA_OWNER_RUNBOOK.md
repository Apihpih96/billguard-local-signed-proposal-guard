# Diana owner runbook (offline preparation only)

Last checked against QoreChain's official CLI and protocol docs: 19 Nov 2026. This is a command reference, not an executed setup. No account address, key, signature, wallet, or transaction is included here. Replace every `REPLACE_…` value locally before use; never paste mnemonics, private keys, PQ keys, possession proofs, or recovery material into chat, a repository, or a shared machine.

## Before touching the chain

Use only a disposable, owner-controlled Diana testnet account with test funds, on an isolated machine. The EVM account must be the account's `eth_secp256k1` / coin-60 identity; the default coin-118 identity is not the EVM signer. Install the official release `qorechaind` binary: the release binary provides PQ `gen-key` and `cosign`; the community build does not. The Diana chain ID is `qorechain-diana`, EVM chain ID 9800, and the documented testnet RPC is `https://rpc-testnet.qore.host:443`.

Read-only preflight (no wallet operation):

```sh
export QNODE='https://rpc-testnet.qore.host:443'
export QCHAIN='qorechain-diana'
export ACCOUNT_ADDRESS='REPLACE_WITH_DISPOSABLE_QOR1_ACCOUNT_ADDRESS'
export ACCOUNT_KEY='REPLACE_WITH_LOCAL_OWNER_KEY_ALIAS'
export PQC_KEY='REPLACE_WITH_LOCAL_PQC_KEY_ALIAS'

qorechaind query abstractaccount config
qorechaind query pqc account "$ACCOUNT_ADDRESS"
qorechaind query abstractaccount account "$ACCOUNT_ADDRESS"
```

Confirm the abstract-account module is enabled, the account and EVM identity are the intended disposable ones, and record any existing rules before changing them. Do not assume an empty result means the account is ready. A linked authenticator is a different control from the EVM window.

## Register the owner's ML-DSA-87 key, only if none is registered

Do not rotate or replace an existing registered key. If needed, generate a local key with the documented release CLI:

```sh
qorechaind tx pqc gen-key "$PQC_KEY"
```

This creates an unencrypted secret file at `~/.qorechaind/pqc/<alias>.dilithium` (mode 0600) and prints the public-key hex. Treat the file as a root signing secret; keep it only on the isolated owner machine and back it up securely.

For an account with no PQ key, the documented first-registration command is an owner-only on-chain action: `--from` signs and broadcasts it (classically, because this is the bootstrap registration). Review the account, printed key, gas and fee at the CLI prompt before confirming; do not add `-y`.

```sh
export PQC_PUBLIC_KEY_HEX='REPLACE_WITH_PUBLIC_KEY_HEX_PRINTED_LOCALLY'
qorechaind tx pqc register-key-v2 dilithium5 "$PQC_PUBLIC_KEY_HEX" hybrid \
  --pqc-key "$PQC_KEY" --from "$ACCOUNT_KEY" --chain-id "$QCHAIN" \
  --gas 600000 --fees 60000uqor
```

The official guide sets gas explicitly; the fee floor is 0.1 uqor per gas. After the owner confirms this write, query the account again and verify the registered key. Stop if the account already has a key or its state is unclear.

## Prepare and open a scoped EVM window

Choose the scope and bounds yourself. The chain accepts 1–17,280 blocks, 1–1,000 transactions, and a positive `max_value`; the value cap must cover native value plus the maximum fees of admitted transactions. Blocks are a height interval, not a wall-clock duration. `--allowed-targets` accepts up to 16 unique `0x` targets and forbids contract creation. Use either `--native-only` for plain QOR transfers only, or `--allowed-targets` for specific EVM recipients; do not combine these as if they were interchangeable. Native-only excludes calldata, contract creation, code recipients and EIP-7702 authorizations.

Set only owner-chosen values locally. `MAX_VALUE` must be a valid positive amount such as an integer `uqor` or `qor` string; `TARGET` must be the exact owner-reviewed EVM target. Fee/gas values below are placeholders too and must satisfy the chain's fee floor and the planned transaction.

```sh
export BLOCKS='REPLACE_WITH_OWNER_CHOSEN_INTEGER_1_TO_17280'
export MAX_TXS='REPLACE_WITH_OWNER_CHOSEN_INTEGER_1_TO_1000'
export MAX_VALUE='REPLACE_WITH_OWNER_CHOSEN_POSITIVE_UQOR_OR_QOR_CAP'
export TX_GAS='REPLACE_WITH_OWNER_CHOSEN_GAS_LIMIT'
export TX_FEE='REPLACE_WITH_OWNER_CHOSEN_FEE_UQOR'
export TARGET='REPLACE_WITH_OWNER_REVIEWED_0X_TARGET'

qorechaind tx pqc open-evm-window "$BLOCKS" "$MAX_TXS" "$MAX_VALUE" \
  --allowed-targets "$TARGET" --from "$ACCOUNT_KEY" --chain-id "$QCHAIN" \
  --node "$QNODE" --gas "$TX_GAS" --fees "$TX_FEE" --generate-only > window.json
```

For native transfers only, use the same command but replace `--allowed-targets "$TARGET"` with `--native-only`. `--generate-only` only writes an unsigned transaction file; it does not sign or broadcast. Inspect the whole file and verify owner, chain, bounds and scope before proceeding.

The next command is explicitly owner-only: `cosign` adds the ML-DSA-87 signature and broadcasts the window-opening transaction, incurring its fee. Opening replaces any existing window and advances the account nonce. Run only after reviewing `window.json` and deciding to make that on-chain change:

```sh
qorechaind tx pqc cosign window.json --from "$ACCOUNT_KEY" --pqc-key "$PQC_KEY" \
  --chain-id "$QCHAIN" --node "$QNODE"
```

After a confirmed result, read the window and verify its exact live bounds/scope before any EVM test. Opening a window is not proof of spending-rule enforcement; the window does not constrain abstract-account executions authorized by authenticators. A later allowed/denied test transaction is a separate owner-approved, fee-bearing action.

## Separate smart-account spending-rule and authenticator setup

Diana's abstract-account module is documented as enabled on testnet (and disabled on mainnet). The official CLI documents these operations, but they are not performed by this package. A value-moving linked key (`send`, `evm`, `svm`, `deploy`, or `all`) needs an enabled rule that bounds every denomination. `update-rules` replaces the complete rule list, so fetch and preserve every rule the owner intends to keep. Rules constrain linked keys, not the owner's root key.

The rule JSON is an owner decision, not a default. Set it locally to a complete valid array using the documented `SpendingRule` fields (`id`, `enabled`, positive `per_tx_limit` and `daily_limit` in base units, `allowed_denoms`, and any needed call restrictions). Use exact denom spelling (`uqor` for native QOR). Then generate an unsigned tx:

```sh
export RULES_JSON='REPLACE_WITH_OWNER_CHOSEN_COMPLETE_VALID_SPENDING_RULES_JSON_ARRAY'
qorechaind tx abstractaccount update-rules "$ACCOUNT_ADDRESS" "$RULES_JSON" \
  --chain-id "$QCHAIN" --from "$ACCOUNT_KEY" --generate-only \
  --gas 400000 --fees 40000uqor > rules.json
```

Inspect `rules.json` and ensure the JSON replaces the existing rules only with the intended complete set. The next `cosign` is owner-only signing plus broadcast and fee payment:

```sh
qorechaind tx pqc cosign rules.json --from "$ACCOUNT_KEY" --pqc-key "$PQC_KEY" \
  --chain-id "$QCHAIN" --node "$QNODE"
```

To link an external key, the owner must choose the key's scheme, exact permissions, expiry and label. From v3.2.8, registration also requires a proof of possession: the linked key signs the exact chain/account/scheme/key link text, not the account owner's key. The CLI's `link-message` command prints the bytes to be signed; this documented example is for an ed25519 key:

```sh
export LINKED_PUBKEY_BASE64='REPLACE_WITH_LINKED_KEY_PUBLIC_KEY_BASE64'
qorechaind tx abstractaccount link-message "$ACCOUNT_ADDRESS" ed25519 \
  "$LINKED_PUBKEY_BASE64" --chain-id "$QCHAIN"
```

Have the owner review that text and obtain the possession proof through the linked key's own wallet `signMessage` flow. Do not send the proof to Wabi or store it in this project. The registration below is generated unsigned; substitute only the owner's selected, valid values locally. The separate root-key `cosign` afterwards is what authorizes/broadcasts registration.

```sh
export LINKED_PERMISSIONS='REPLACE_WITH_MINIMUM_OWNER_CHOSEN_PERMISSION'
export LINKED_EXPIRY_UNIX='REPLACE_WITH_OWNER_CHOSEN_UNIX_EXPIRY'
export LINKED_LABEL='REPLACE_WITH_OWNER_CHOSEN_LABEL'
export POSSESSION_PROOF_BASE64='REPLACE_WITH_LINKED_WALLET_SIGNATURE_BASE64'
qorechaind tx abstractaccount register-authenticator "$ACCOUNT_ADDRESS" ed25519 \
  "$LINKED_PUBKEY_BASE64" "$LINKED_PERMISSIONS" "$LINKED_EXPIRY_UNIX" "$LINKED_LABEL" \
  --possession-proof "$POSSESSION_PROOF_BASE64" --chain-id "$QCHAIN" \
  --from "$ACCOUNT_KEY" --generate-only --gas 400000 --fees 40000uqor > link.json
```

Inspect the complete link transaction before owner-only hybrid signing/broadcast:

```sh
qorechaind tx pqc cosign link.json --from "$ACCOUNT_KEY" --pqc-key "$PQC_KEY" \
  --chain-id "$QCHAIN" --node "$QNODE"
```

This CLI example is for ed25519. For a MetaMask/secp256k1 key, the possession proof is EIP-191 `personal_sign` over the chain/account/scheme/key link text; use the official v0.14 SDK/wallet-adapter `metaMaskPossessionProof` and `linkAuthenticatorMsgs` path only after independently validating inputs and decoded messages. The adapter does not allow these authority-changing messages through its QoreX `qorexSignAndBroadcast` path. Account-level rules should be set before linking a value-moving key, or together in one root-authorized transaction using the SDK helper. Verify the included transaction result, then query the account's authenticators and spending rules. A relayer and a separately approved test execution are still needed to demonstrate the linked key's bounded behavior; check the execution's `success`/failure event, not only transaction code.

## What this package still cannot claim

The bounty asks for a scoped EVM window, transaction/value/duration/target limits, smart-account spending rules, and authenticated messaging. The runbook documents preparation steps; it did not execute any setup or test. A real result still needs a disposable account, owner-chosen bounds/rules/key permissions/expiry, owner signatures and broadcasts, then observed Diana state and allowed/denied execution receipts.

The remaining messaging blocker is different: the bounty brief says “authenticated messaging” but does not define a protocol, transport, trust model, required demo, or evidence criterion. The QoreSign local demo proves only that a synthetic message can be signed and verified; it has no agent-to-agent transport and is not confirmed to satisfy the bounty. The clarification email to `team@qorechain.io` has no reply in the latest mailbox search (19 Nov 2026); do not claim this requirement is met until the organizers clarify it.

## Official references

- [EVM Authorisation Window Reference](https://docs.qorechain.io/developer-guide/evm-window-reference/)
- [EVM Development](https://docs.qorechain.io/developer-guide/evm-development/)
- [Post-Quantum Signing](https://docs.qorechain.io/developer-guide/post-quantum-signing/)
- [Account Abstraction](https://docs.qorechain.io/developer-guide/account-abstraction/)
- [Wallet Adapter](https://docs.qorechain.io/developer-tools/wallet-adapter/)
- [QoreX overview](https://docs.qorechain.io/qorex/overview/)
- [Build Before Q-Day bounty page](https://build.qorechain.io/)
