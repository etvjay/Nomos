"""Verified Receivable -- downstream composition of Claim Verification + Claim Encumbrance.

This is the application composition layer for a verified-receivable flow. It
consumes ONLY the public method surface declared by the two primitives'
CAPABILITY.json contracts:

  claim-verification (SEMANTIC / judgment-bearing):
      has_verification, get_verification -> canonical decision JSON
  claim-encumbrance (EXACT / deterministic):
      set_financeable_amount, reserve, financeable_amount,
      active_encumbrances, get_encumbrance

Composition gate
----------------
Capital is only reserved against a claim AFTER a Claim Verification decision
with status VERIFIED exists for that claim. A missing decision or any
non-VERIFIED decision (CONFLICTED / INSUFFICIENT / UNDETERMINED) rejects the
reservation before the encumbrance primitive is touched.

Deployment note
---------------
GenLayer SDK v0.18 (py-genlayer 1jb45...) has no cross-contract call API, so a
GenLayer contract cannot itself invoke the two primitives. This module is the
composable application layer: it is given the deployed primitive instances and
composes them through their public method surfaces only. Tests deploy both
primitives with the direct-mode fixtures and drive this layer.
"""

import json


class VerifiedReceivable:
    """Composes a Claim Verification contract with a Claim Encumbrance contract.

    Args:
        verification: deployed Claim Verification contract instance.
        encumbrance: deployed Claim Encumbrance contract instance.
    """

    def __init__(self, verification, encumbrance):
        self.verification = verification
        self.encumbrance = encumbrance

    def get_decision(self, verification_id):
        raw = self.verification.get_verification(verification_id)
        if not raw:
            return None
        return json.loads(raw)

    def is_verified(self, verification_id):
        decision = self.get_decision(verification_id)
        return decision is not None and decision["status"] == "VERIFIED"

    def prepare_claim(self, claim_id, financeable_amount):
        """Set the immutable financeable capacity for a claim (idempotent app setup)."""
        return json.loads(
            self.encumbrance.set_financeable_amount(claim_id, financeable_amount)
        )

    def financeable_balance(self, claim_id):
        return {
            "financeable_amount": self.encumbrance.financeable_amount(claim_id),
            "active_encumbrances": self.encumbrance.active_encumbrances(claim_id),
        }

    def reserve_against_verified_claim(
        self, verification_id, claim_id, reservation_id, amount
    ):
        """Reserve capital against a claim only if a VERIFIED decision exists.

        Raises ValueError if the verification is missing or not VERIFIED, or if
        the decision does not belong to the target claim. On success returns the
        canonical encumbrance record from the encumbrance primitive.
        """
        decision = self.get_decision(verification_id)
        if decision is None:
            raise ValueError(
                "VerifiedReceivable: no verification decision for verification_id "
                + verification_id
            )
        if decision["status"] != "VERIFIED":
            raise ValueError(
                "VerifiedReceivable: decision not VERIFIED "
                + "(status=" + decision["status"] + ")"
            )
        if decision["claim_id"] != claim_id:
            raise ValueError(
                "VerifiedReceivable: verification claim_id "
                + decision["claim_id"]
                + " does not match target claim_id " + claim_id
            )
        return json.loads(
            self.encumbrance.reserve(reservation_id, claim_id, amount)
        )