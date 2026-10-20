"""Deterministic validation for GenLayer adjudication-to-action receipts.

This module is intentionally free of LLM/web calls. GenLayer produces the
adjudication result; this module checks whether that result is sufficiently
bound and current to become an Intelligent Account proposal or action.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


TERMINAL_DECISIONS = {"ACCEPTED", "REJECTED", "UNDETERMINED"}
ACTIONABLE_DECISION = "ACCEPTED"


class ReceiptError(ValueError):
    """A receipt cannot authorize a proposal or action."""


def _require_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"missing or invalid {key}")
    return value.strip()


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ReceiptError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ReceiptError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def validate_adjudication_receipt(
    receipt: Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, str]:
    """Validate the stable receipt fields required by an account proposal.

    Validation is fail-closed. In particular, REJECTED and UNDETERMINED are
    valid recorded outcomes but can never authorize execution.
    """
    required = (
        "decision_id",
        "source_contract",
        "question_hash",
        "evidence_hash",
        "decision_status",
        "equivalence_mode",
        "policy_version",
        "created_at",
        "expires_at",
    )
    for key in required:
        _require_text(receipt, key)

    status = receipt["decision_status"]
    if status not in TERMINAL_DECISIONS:
        raise ReceiptError("invalid decision_status")
    if receipt["equivalence_mode"] not in {"comparative", "non_comparative", "custom", "strict"}:
        raise ReceiptError("invalid equivalence_mode")

    created = _parse_time(receipt["created_at"])
    expires = _parse_time(receipt["expires_at"])
    if expires <= created:
        raise ReceiptError("expires_at must follow created_at")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= expires:
        raise ReceiptError("receipt expired")

    return {
        "decision_id": receipt["decision_id"],
        "decision_status": status,
        "policy_version": receipt["policy_version"],
        "actionability": "ACTIONABLE" if status == ACTIONABLE_DECISION else "NON_ACTIONABLE",
    }


def bind_proposal(
    receipt: Mapping[str, Any], proposal: Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Return a proposal record only when receipt and action are bound."""
    validated = validate_adjudication_receipt(receipt, now=now)
    if validated["actionability"] != "ACTIONABLE":
        raise ReceiptError("only ACCEPTED adjudications may create executable proposals")
    if _require_text(proposal, "proposal_id") == "":
        raise ReceiptError("missing proposal_id")
    if _require_text(proposal, "decision_id") != validated["decision_id"]:
        raise ReceiptError("proposal decision_id mismatch")
    if _require_text(proposal, "policy_version") != validated["policy_version"]:
        raise ReceiptError("proposal policy_version mismatch")
    return {
        "proposal_id": proposal["proposal_id"],
        "decision_id": validated["decision_id"],
        "policy_version": validated["policy_version"],
        "status": "PROPOSED",
    }
