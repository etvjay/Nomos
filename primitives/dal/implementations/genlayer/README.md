# DAL — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Implement keyed/2D replay state suitable for authorization-scoped lanes.
- Bind replay consumption to exact authorization identity and domain.
- Ensure failed validation does not consume successful-execution replay state unless canonical semantics explicitly require otherwise.
- Preserve independent lane progress while exposing shared dependency failures separately.

## Intelligence boundary
NONE. Never use validator/LLM judgment for nonce validity, replay detection, sequence advancement, or authorization identity.

## Required evidence
GenVM lint, direct tests, same-issuer independent-authorization tests, replay tests, shared-capacity conflict tests, canonical vectors, integration tests, and deployment/CLI evidence.
