# Capital Commitment — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Track committed capacity against exact allocation/pool/asset/beneficiary identifiers.
- Make active commitments unavailable to competing withdrawals/allocations.
- Implement reserve, release, expiry, and settle transitions deterministically.
- Preserve atomicity between commitment creation and backing-capacity accounting.

## Intelligence boundary
NONE for commitment accounting. Do not insert judgment into conservation, reservation, or expiry.

## Required evidence
GenVM lint, direct tests, overcommit/withdrawal race tests, canonical vectors, integration tests, and deployment/CLI evidence.
