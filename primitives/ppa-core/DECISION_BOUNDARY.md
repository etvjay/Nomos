# Decision Boundary

`JUDGMENT_BOUNDARY = NONE`. This component is deterministic and implemented as
such. Substantive judgment — whether external evidence supports a conclusion —
belongs to a separate adjudication producer contract and is not implemented here.

This component does not produce `ACCEPTED`/`REJECTED`/`UNDETERMINED`. It only
verifies a caller and revalidates consequence/
deterministic gates. No judgment output can move funds directly.
