export type ClaimVerificationStatus =
  | "VERIFIED"
  | "CONFLICTED"
  | "INSUFFICIENT"
  | "UNDETERMINED";

export type ClaimVerificationReasonCode =
  | "EVIDENCE_SUPPORTS_CLAIM"
  | "MATERIAL_CONFLICT"
  | "MISSING_ESSENTIAL_EVIDENCE"
  | "EVIDENCE_AMBIGUOUS";

export interface ClaimVerificationRequest {
  verificationId: string;
  claimId: string;
  evidenceDigest: string;
  claim: Record<string, unknown>;
  evidence: Record<string, unknown> | unknown[];
}

export interface ClaimVerificationDecision {
  verification_id: string;
  claim_id: string;
  evidence_digest: string;
  status: ClaimVerificationStatus;
  reason_code: ClaimVerificationReasonCode;
  requested_by: string;
}

export function parseClaimVerificationDecision(
  raw: string,
): ClaimVerificationDecision {
  const parsed = JSON.parse(raw) as ClaimVerificationDecision;
  return parsed;
}
