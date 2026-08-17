# Workflow Authorization — Canonical Specification

Status: RESEARCHING
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
GenLayer MAY judge whether an action is substantively within delegated purpose or whether proposed terms satisfy a natural-language authority mandate. Reference continuity, signatures, expiry, capability bounds, and quantitative limits remain deterministic.

## Composition
Consumes Policy Envelope and evidence; feeds DAA, Capital Commitment, DAL, Settlement, Financial Contract, and Gaia correction workflows.
