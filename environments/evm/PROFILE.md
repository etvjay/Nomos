# EVM Environment Profile

Role: deterministic execution and safety substrate for Nomos primitives and adapters.

## Mapping

- deterministic state transitions: `NATIVE`
- signatures/account validation: `NATIVE` or `ADAPTER`
- replay/nonce enforcement: `NATIVE` or `ADAPTER`
- capacity/encumbrance/commitment accounting: `NATIVE`
- ERC-20 settlement: `ADAPTER`
- vault/pool mechanics: `ADAPTER`
- subjective external-world judgment: `EXTERNAL` unless composed with a judgment substrate

## Standards rule

ERC/EIP/RIP standards are implementation machinery or prior art unless the canonical spec explicitly establishes semantic equivalence.

Potential adapters include typed data, contract signatures, account abstraction, delegation, vaults and token settlement. Each adapter must be named, versioned where applicable, and conformance-tested.

## Constitutional boundary

Do not force judgment-bearing semantics into deterministic predicates merely to remain EVM-only. If the canonical question requires interpretation of heterogeneous external evidence or qualitative mandates, use an explicit adjudication adapter/profile and preserve its trust assumptions.

## Reject

- mapping-only 'reservation' that can be drained underneath;
- allowances mistaken for commitments;
- nonce independence mistaken for economic-state independence;
- proof hashes used as stable economic claim identity;
- external oracle/admin decisions represented as deterministic protocol truth without provenance;
- standards compatibility claimed without executable adapter tests.
