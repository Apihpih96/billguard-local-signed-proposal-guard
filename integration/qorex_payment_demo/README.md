# BillGuard QoreX owner-reviewed Diana transfer scaffold

This is a small browser integration scaffold based on the official QoreChain wallet-adapter documentation (`@qorechain/wallet-adapter` 0.6.0). It constructs one native `/cosmos.bank.v1beta1.MsgSend` and, only after a separate click, hands that exact message to QoreX. QoreX displays the decoded transaction; its owner must approve there before QoreX signs and broadcasts. This package has not invoked QoreX or sent a transaction.

## Run the focused tests

From this directory, run `npm test` with Node.js 20+. The tests use injected stand-ins for the wallet and protobuf encoder; they do not require QoreX, an account, network access, keys, or funds.

## Run the browser scaffold

Install dependencies with `npm install`, then run `npm run dev` and open the local URL in a browser with QoreX available. The page does not request the current wallet address automatically: the owner types the sender, recipient and positive integer amount in `uqor`, reviews the displayed transfer, clicks “Open QoreX to review this transfer,” and then decides inside QoreX. The app never switches wallet networks. The wallet must already be on `qorechain-diana` and use a QoreX version supported by the adapter (extension >=0.3.5 or app >=1.1.5, as stated in the official docs).

No mnemonic, private key, PQC secret or recovery code is asked for, copied, or stored. Do not use a valuable account. Only use a disposable funded Diana test account when deliberately testing the flow.

## Important limits

This is an ordinary user-authorized native QOR transfer, not an autonomous BillGuard transaction. The local form has no on-chain spending-rule integration, no EVM authorization window, no linked authenticator, and no agent messaging. It does not enforce a recipient cap against a malicious or modified client. The QoreX approval is a human wallet confirmation, not proof that BillGuard's agent policy is enforced. A returned transaction hash is not independently checked against a Diana block explorer by this scaffold.

The current environment's anonymous Diana account reads returned HTTP 403; that did not establish account setup or testnet readiness. Before a genuine bounded-agent test, the account owner must provide/authorize a disposable Diana test account and separately review any required registration, authenticator/spending-rule/window setup and any payment. This code does not perform those setup actions or broadcast during its tests.

Official reference: https://docs.qorechain.io/developer-tools/wallet-adapter/ (read 19 Nov 2026). The official page says the QoreX signing examples have not been run end-to-end and describes `qorexSignAndBroadcast` as passing messages to QoreX for its review, hybrid signing and broadcast.


## Setup boundary (checked 19 Nov 2026)

QoreX itself documents an owner-operated EVM-window card at Settings → Security → EVM access window (mobile) or the EVM access window button in the extension popup. It requires an Ethereum-style coin-60 account and asks the owner to approve `MsgOpenEVMWindow` with blocks, transaction count, and a QOR value cap including max fees. The QoreX card does not expose `native_only` / `allowed_targets`, and the wallet-adapter refuses `MsgOpenEVMWindow` through this web integration. This scaffold does not create that window.

The wallet-adapter also refuses authenticator registration/revocation and spending-rule updates; QoreX docs say linked Phantom/MetaMask signers with spending limits are not yet available inside QoreX. A separate Dashboard Phantom flow requires Keplr and is not a QoreX route. So no safe setup flow for scoped EVM windows or linked-authenticator spend limits is implemented here. The successful local tests only cover request construction/readiness checks; they do not establish or mutate chain state.
