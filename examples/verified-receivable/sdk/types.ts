/**
 * Verified Receivable -- composition-level SDK types (EXP-CONV-002, lane D).
 *
 * Ties the Claim Verification SDK decision type to the Claim Encumbrance
 * canonical record/views. The ClaimVerificationDecision shape below mirrors
 * the canonical decision type in the claim-verification SDK (sdk-cv-types.ts,
 * supplied in the composition lane); ClaimEncumbrance* shapes mirror the
 * claim-encumbrance CAPABILITY.json. This file does NOT modify the primitive
 * SDK files; it only composes them for downstream use.
 */

/** Canonical status of a Claim Verification decision (SDK: ClaimVerificationStatus). */
export type ClaimVerificationStatus =
  | "VERIFIED"
  | "CONFLICTED"
  | "INSUFFICIENT"
  | "UNDETERMINED";

/** Canonical decision JSON returned by ClaimVerification.get_verification. */
export interface ClaimVerificationDecision {
  verification_id: string;
  claim_id: string;
  evidence_digest: string;
  status: ClaimVerificationStatus;
  reason_code: string;
  requested_by: string;
}

/** Canonical Claim Encumbrance lifecycle statuses (CAPABILITY.json). */
export type EncumbranceStatus =
  | "RESERVED"
  | "COMMITTED"
  | "RELEASED"
  | "SETTLED";

/** Canonical encumbrance record returned by ClaimEncumbrance.reserve/commit/etc. */
export interface EncumbranceRecord {
  reservation_id: string;
  claim_id: string;
  amount: string;
  status: EncumbranceStatus;
}

/** Canonical views returned by the Claim Encumbrance primitive. */
export interface ClaimEncumbranceViews {
  financeable_amount: string;
  active_encumbrances: string;
}

/** Composition decision: reserve is only allowed for a VERIFIED claim. */
export type ReserveOutcome =
  | { allowed: true; record: EncumbranceRecord }
  | {
      allowed: false;
      reason:
        | "MISSING_VERIFICATION"
        | "NOT_VERIFIED"
        | "CLAIM_MISMATCH"
        | "ENCUMBRANCE_REJECTED";
    };

/** True only when the canonical decision status is VERIFIED. */
export function isVerified(decision: ClaimVerificationDecision): boolean {
  return decision.status === "VERIFIED";
}