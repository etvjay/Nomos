# Adjudicated Receipt - Threat Model

Test evidence source spoofing (evidence_pointer content substitution), stale evidence authorization (adjudication or settlement past TTL), receipt replay (duplicate ids, post-consumption reuse, cross-invoice or cross-contract redirection), receipt-id collision, invoice term substitution after a receipt is recorded, validator disagreement and false convergence, LLM schema evasion (free-form output smuggled in as approval), low-confidence and partial-delivery acceptance pressure, TTL bypass, keeper-driven griefing (permissionless ticks that settle nothing), pre-quorum or non-owner settlement, evidence omission, prompt/evidence manipulation, and judgment overriding surrender value, asset, or payee.

Fail closed into explicit non-acceptance states. Every adversarial path must leave no release, no phantom receipt, and no partial consumption.
