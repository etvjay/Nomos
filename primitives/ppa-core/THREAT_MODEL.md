# Threat Model

Replay of settled payment ids, denied-id retry abuse, balance overcommit,
daily-window manipulation, stale/expired/revoked evidence authorizing new state,
attestation substitution under another subject, unauthorized issuers,
policy-version drift, provider outage mistaken for approval, and partial
execution leaving an impossible balance.

For the boundary specifically: caller-identity spoofing via a JSON source field,
an unregistered or revoked caller crossing the boundary, an intermediary widening
amount, recipient, or policy, and a silent refusal that leaves no audit artifact.
Caller semantics are evidenced by convergence/reports/CALLER-IDENTITY-SPIKE.json.
