# Proof of Payable — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

This directory is mandatory. Executable implementation evidence must replace this status before the primitive can become `CONFORMANT`.

## Required GenLayer behavior
- Accept canonical claim identity, lifecycle state, evidence references, and lineage.
- Preserve deterministic `claimId`, versioning, hash, amount, and transition checks.
- Where configured, use Intelligent Contract judgment only to decide whether admissible heterogeneous evidence supports the claimed payable state.
- Produce a structured decision, never free-form authority to move value.
- Support an explicit `UNDETERMINED` result.
- Persist or emit canonical decision/evidence commitments required by the spec.

## Must never do
- create a new claim merely because evidence changed;
- treat model output as capital authority;
- bypass lifecycle legality;
- silently map contradictory evidence to approval.

## Required evidence before status advancement
GenVM lint, direct tests, canonical Nomos vectors, integration tests for judgment-bearing paths, and deployment/CLI evidence appropriate to the target GenLayer network.
