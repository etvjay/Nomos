# Adjudicated Receipt - Decision Boundary

GenLayer judges exactly one question per adjudication: does the evidence fetched in-transaction from the registered evidence pointer satisfy the registered adjudication clause for releasing this object? It emits the bounded triple (satisfied, verdict, confidence) plus a reason string.

Judgment cannot change object identity or registered terms, surrender value, asset, or payee. It cannot create policy, allocation, commitment, encumbrance, or settlement state. It cannot turn uncertainty, partial delivery, low confidence, malformed output, or validator disagreement into acceptance. Its verdict authorizes nothing until the deterministic settlement gate admits it: receipt ACCEPTED, unconsumed, bound to the current invoice terms, unexpired at record and at settle time, executed by the owner for the single registered surrender value.

Adjudication ticks are permissionless for liveness; triggering one confers no settlement right. Settlement is owner-held in v0.1 and records a release obligation, not a token transfer (token rails are an explicit NOT_IMPLEMENTED downstream surface consumed via composition).
