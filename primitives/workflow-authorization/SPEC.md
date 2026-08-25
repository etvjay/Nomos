# Workflow Authorization - Canonical Specification

Status: SPECIFIED
Version: 0.1.0

## Problem
Preserve authority continuity across a multi-step economic workflow so execution is valid only when actor, standing delegation, workflow state, accepted agreement, evidence, and requested action remain mutually consistent.

## Primitive meaning
Workflow Authorization composes Path (standing bounded delegated authority) and Pact (specific accepted economic relation) around an intent/proposal/decision chain.

## Core invariants
- Path does not allocate capital.
- Pact does not create standing delegation or guarantee backing capital.
- Revoked/expired Path cannot authorize later execution.
- Pact must bind the exact authorized workflow and accepted terms.
- A blocked decision cannot produce an executable Pact.
- Direct exact-wallet authorization may have a reduced chain only when the canonical profile explicitly permits it.

## Judgment boundary
NONE for the v0.1 canonical slice. Reference continuity, capability membership, quantitative limits, expiry, revocation, and exact Pact binding are deterministic and implemented as such. Substantive purpose/mandate-fit judgment is delegated to Policy Envelope's interpret_clause surface consumed before Pact proposal; its result can never relax the deterministic gates here.

### v0.1 classification change (Article XVI record)
v0.1-draft declared judgmentBearing=true (SEMANTIC). Accepted v0.1 narrows the canonical surface to deterministic Path/Pact machinery with externalized judgment (policy-envelope). Compatibility: additive; no prior release consumed a SEMANTIC workflow-authorization surface.

## Composition
Consumes Policy Envelope and evidence; feeds DAA, Capital Commitment, DAL, Settlement, Financial Contract, and Gaia correction workflows.
