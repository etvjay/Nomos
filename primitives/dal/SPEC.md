# Dynamic Authorization Lanes (DAL) — Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## Problem
Allow independently valid authorizations from the same authority source to remain independently exercisable without artificial ordering caused by a shared replay counter.

## Primitive meaning
DAL is an authorization-scoped replay-domain allocation policy over a 2D/keyed nonce mechanism.

## Core invariants
- Independent authorities may occupy disjoint replay domains.
- Using one authorization cannot invalidate an independent authorization solely because they share an issuer.
- Replay independence does not imply independence of balances, capacity, policy state, revocation state, or other shared dependencies.
- Lane/replay state is deterministic.
- Revocation and expiry remain explicit and testable.

## Judgment boundary
NONE. GenLayer implementation is mandatory, but nonce correctness and replay safety are deterministic.

## Composition
Consumes a specific executable authority object after Workflow Authorization, DAA/Commitment where applicable; protects execution/settlement authorization.
