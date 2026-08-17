# DAL — Invariants

- Independent authorizations may use independent replay domains.
- Exercising one cannot invalidate another solely because they share an issuer.
- Replay independence does not imply independence of shared economic state.
- Nonce/lane validity and advancement are deterministic.
- Revocation and expiry are explicit.
