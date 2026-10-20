# Invariants

- Funds move only through the deterministic gate sequence.
- No method mutates balances outside deposit/withdraw/settlement paths with their own authority checks.
- A DENY moves no funds, consumes no payment id, and records an auditable reason.
- A payment id reaches a non-DENIED terminal state at most once.
- `available = balance - committed` is the only spendable capacity.
- Origin is the actual caller address, never a JSON field.
- Every inbound execution attempt produces exactly one auditable outcome: EXECUTED, DENIED, or REJECTED.
- A refusal that leaves no observable artifact is a contract violation.
