"""Programmable Payment Account (PPA) — independent reimplementation.

Nomos primitive: ppa | capability 0.1.0 | convergence mode: EXACT
JUDGMENT_BOUNDARY = NONE (deterministic rule evaluation only)

Canonical v0.1 slice implemented (the surface exercised by the canonical
vectors):
  initialize, create_account, deposit, send, get_account, get_payment,
  register_attestation, revoke_attestation, get_attestation

send() gate order:
  1. policy gate   — denylist/allowlist deny, per-tx limit, daily limit over
                     a rolling 86400s window;
  2. attestation gate — only when rules.require_attestation is truthy;
                     fail-closed (absent/stale/revoked/malformed evidence can
                     never admit a payment; unavailability is a denial);
  3. encumbrance gate — available = balance - committed, else
                     INSUFFICIENT_COMMITMENT;
  4. settle        — deduct balance, record daily spend event, record the
                     SETTLED payment.

A DENIED send records an auditable denial decision, moves no funds, updates
no daily window, and does NOT consume the payment id (retry with the same id
is allowed, e.g. after a rule change or once valid evidence appears). Any
non-DENIED terminal record consumes its payment id exactly once; a replay of
a settled id is a structural rejection.

Attestations are owner-registered technical-compliance evidence with a fixed
schema (exactly subject, issuer, status, issued_at, expires_at, evidence_hash,
policy_version); status vocabulary is VALID|REVOKED; unknown or missing
fields, non-ISO timestamps, and duplicate ids are rejected at registration.
Revocation flips status to REVOKED and affects future sends only.

Fixed simulated chain time NOW makes the 2020-issued/2099-expiring
attestation currently valid and the 2020-issued/2021-expiring one expired.

Embedded vector runner (mirrors tools/nomos_run_vectors.py dispatch
semantics: "ok" = no exception, "reject" = exception, dict expect = subset
field match, fresh contract instance per vector):

    python3 your_build.py <vectors.json>
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

JUDGMENT_BOUNDARY = "NONE"

# Fixed simulated chain time for the v0.1 canonical slice.
NOW = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

DAILY_WINDOW_SECONDS = 86400

ATTESTATION_FIXED_FIELDS = frozenset(
    (
        "subject",
        "issuer",
        "status",
        "issued_at",
        "expires_at",
        "evidence_hash",
        "policy_version",
    )
)
ATTESTATION_STATUSES = frozenset(("VALID", "REVOKED"))
ATTESTATION_ID_MAX_CHARS = 64
EVIDENCE_HASH_MAX_CHARS = 128
POLICY_VERSION_MAX_CHARS = 64

STATUS_SETTLED = "SETTLED"
STATUS_DENIED = "DENIED"


class PpaError(Exception):
    """Deterministic structural/validation rejection (never a gate decision)."""


def canonical(obj) -> str:
    """Canonical serialization: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _require_str(value, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise PpaError(f"INVALID_{name}")
    return value


def _require_uint(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise PpaError(f"INVALID_{name}")
    text = str(value)
    if not text.isdigit():
        raise PpaError(f"INVALID_{name}")
    amount = int(text)
    if amount <= 0:
        raise PpaError(f"INVALID_{name}")
    return amount


def _parse_ts(value) -> datetime:
    if not isinstance(value, str):
        raise PpaError("ATTESTATION_INVALID")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise PpaError("ATTESTATION_INVALID")
    if parsed.tzinfo is None:
        raise PpaError("ATTESTATION_INVALID")
    return parsed


class Ppa:
    """PPA contract state machine.

    Owns ONLY the sub-account ledger, payment records, and owner-registered
    technical-compliance attestations. No judgment output can move funds;
    only the deterministic gates admit a payment.
    """

    def __init__(self):
        self._initialized = False
        self._owner = None
        self._accounts = {}
        self._payments = {}
        self._attestations = {}

    # ------------------------------------------------------------------ #
    # write methods                                                      #
    # ------------------------------------------------------------------ #

    def initialize(self, owner: str) -> str:
        if self._initialized:
            raise PpaError("ALREADY_INITIALIZED")
        _require_str(owner, "OWNER")
        self._owner = owner
        self._initialized = True
        return "ok"

    def create_account(self, account_id: str, rules_json: str) -> str:
        self._require_initialized()
        _require_str(account_id, "ACCOUNT_ID")
        if account_id in self._accounts:
            raise PpaError("ACCOUNT_EXISTS")
        rules = self._parse_rules(rules_json)
        self._accounts[account_id] = {
            "account_id": account_id,
            "rules": rules,
            "balance": 0,
            "committed": 0,
            # rolling daily window: (timestamp, amount) settle events
            "spends": [],
        }
        return "ok"

    def deposit(self, account_id: str, amount: str) -> str:
        self._require_initialized()
        account = self._require_account(account_id)
        account["balance"] += _require_uint(amount, "AMOUNT")
        return "ok"

    def send(self, account_id: str, payment_id: str, to: str, amount: str,
             evidence_hash: str = "", memo: str = "") -> str:
        self._require_initialized()
        account = self._require_account(account_id)
        _require_str(payment_id, "PAYMENT_ID")
        _require_str(to, "RECIPIENT")
        value = _require_uint(amount, "AMOUNT")

        # A payment id is consumed exactly once by a non-DENIED terminal
        # record; a prior DENIED record leaves the id retryable.
        prior = self._payments.get(payment_id)
        if prior is not None and prior["status"] != STATUS_DENIED:
            raise PpaError("PAYMENT_ID_CONSUMED")

        reason = (
            self._policy_gate(account, to, value)
            or self._attestation_gate(account, to)
            or self._encumbrance_gate(account, value)
        )

        base = {
            "payment_id": payment_id,
            "account_id": account_id,
            "to": to,
            "amount": str(value),
            "evidence_hash": evidence_hash,
            "memo": memo,
        }

        if reason is not None:
            # DENY: no funds move, no daily spend event, no id consumption;
            # the auditable denial record is stored (latest denial per id).
            record = dict(base, status=STATUS_DENIED, reason=reason,
                          created_at=NOW.isoformat())
            self._payments[payment_id] = record
            return canonical({"status": STATUS_DENIED, "reason": reason,
                              "payment_id": payment_id, "amount": str(value)})

        # Settle: deduct balance, record the rolling-window spend event,
        # record immutable SETTLED history, consume the payment id.
        account["balance"] -= value
        account["spends"] = [
            (ts, v) for ts, v in account["spends"]
            if NOW - ts < timedelta(seconds=DAILY_WINDOW_SECONDS)
        ]
        account["spends"].append((NOW, value))
        self._payments[payment_id] = dict(
            base, status=STATUS_SETTLED, created_at=NOW.isoformat())
        return canonical({"status": STATUS_SETTLED, "payment_id": payment_id,
                          "amount": str(value)})

    def register_attestation(self, attestation_id: str,
                             attestation_json: str) -> str:
        self._require_initialized()
        _require_str(attestation_id, "ATTESTATION_ID")
        if len(attestation_id) > ATTESTATION_ID_MAX_CHARS:
            raise PpaError("ATTESTATION_ID_TOO_LONG")
        if attestation_id in self._attestations:
            raise PpaError("ATTESTATION_EXISTS")
        if not isinstance(attestation_json, str):
            raise PpaError("ATTESTATION_SCHEMA_VIOLATION")
        try:
            record = json.loads(attestation_json)
        except json.JSONDecodeError:
            raise PpaError("ATTESTATION_SCHEMA_VIOLATION")
        # Fixed schema: exactly the seven fields, all strings; unknown fields
        # (PII carriers) and missing fields are both rejected.
        if (not isinstance(record, dict)
                or set(record) != ATTESTATION_FIXED_FIELDS
                or any(not isinstance(record[f], str)
                       for f in ATTESTATION_FIXED_FIELDS)):
            raise PpaError("ATTESTATION_SCHEMA_VIOLATION")
        if record["status"] not in ATTESTATION_STATUSES:
            raise PpaError("ATTESTATION_INVALID_STATUS")
        if len(record["evidence_hash"]) > EVIDENCE_HASH_MAX_CHARS:
            raise PpaError("ATTESTATION_EVIDENCE_HASH_TOO_LONG")
        if len(record["policy_version"]) > POLICY_VERSION_MAX_CHARS:
            raise PpaError("ATTESTATION_POLICY_VERSION_TOO_LONG")
        _parse_ts(record["issued_at"])
        _parse_ts(record["expires_at"])
        self._attestations[attestation_id] = dict(record)
        return "ok"

    def revoke_attestation(self, attestation_id: str) -> str:
        record = self._attestations.get(attestation_id)
        if record is None:
            raise PpaError("UNKNOWN_ATTESTATION")
        if record["status"] == "REVOKED":
            raise PpaError("ATTESTATION_ALREADY_REVOKED")
        # Affects future sends only; payment history is never rewritten.
        record["status"] = "REVOKED"
        return "ok"

    # ------------------------------------------------------------------ #
    # view methods                                                       #
    # ------------------------------------------------------------------ #

    def get_account(self, account_id: str) -> str:
        account = self._require_account(account_id)
        return canonical({
            "account_id": account["account_id"],
            "currency": account["rules"].get("currency", ""),
            "balance": str(account["balance"]),
            "committed": str(account["committed"]),
            "daily_spent": str(self._daily_spent(account)),
        })

    def get_payment(self, payment_id: str) -> str:
        record = self._payments.get(payment_id)
        if record is None:
            raise PpaError("UNKNOWN_PAYMENT")
        return canonical(dict(record))

    def get_attestation(self, attestation_id: str) -> str:
        record = self._attestations.get(attestation_id)
        if record is None:
            raise PpaError("UNKNOWN_ATTESTATION")
        return canonical(dict(record))

    # ------------------------------------------------------------------ #
    # gates                                                              #
    # ------------------------------------------------------------------ #

    def _policy_gate(self, account: dict, to: str, amount: int):
        """Deterministic policy envelope. Returns a denial reason or None."""
        rules = account["rules"]
        denylist = rules.get("denylist") or []
        if to in denylist:
            return "POLICY_DENYLIST"
        allowlist = rules.get("allowlist") or []
        if allowlist and to not in allowlist:
            # The canonical reason vocabulary has no separate allowlist code;
            # an allowlist miss is reported as POLICY_DENYLIST.
            return "POLICY_DENYLIST"
        per_tx = rules.get("per_tx_limit")
        if per_tx is not None and amount > int(per_tx):
            return "POLICY_PER_TX_LIMIT"
        daily = rules.get("daily_limit")
        if daily is not None:
            if self._daily_spent(account) + amount > int(daily):
                return "POLICY_DAILY_LIMIT"
        return None

    def _attestation_gate(self, account: dict, to: str):
        """Fail-closed admissibility of owner-registered attestations.

        Runs only when rules.require_attestation is truthy. Returns a denial
        reason or None (admit). An empty registry is ATTESTATION_MISSING; a
        non-empty registry with no subject-bound candidate is
        ATTESTATION_SUBJECT_MISMATCH. Bound candidates (subject == recipient,
        regardless of status) are evaluated in ascending attestation_id order
        and the first fully admissible candidate admits the payment.
        """
        rules = account["rules"]
        if not rules.get("require_attestation"):
            return None
        if not self._attestations:
            return "ATTESTATION_MISSING"
        candidates = sorted(
            aid for aid, rec in self._attestations.items()
            if rec["subject"] == to
        )
        if not candidates:
            return "ATTESTATION_SUBJECT_MISMATCH"
        reason = None
        for aid in candidates:
            candidate_reason = self._evaluate_candidate(
                rules, self._attestations[aid])
            if candidate_reason is None:
                return None
            reason = candidate_reason
        return reason

    @staticmethod
    def _evaluate_candidate(rules: dict, record: dict):
        """Per-candidate check order (documented in BUILD_REPORT.md):
        REVOKED -> INVALID_STATUS -> ISSUER_UNAUTHORIZED ->
        POLICY_MISMATCH -> time window (not-yet-valid -> expired).
        Admit iff issued_at <= NOW < expires_at.
        """
        if record["status"] == "REVOKED":
            return "ATTESTATION_REVOKED"
        if record["status"] not in ATTESTATION_STATUSES:
            # Unreachable via registration (status vocabulary enforced there);
            # kept as a defensive fail-closed branch.
            return "ATTESTATION_INVALID_STATUS"
        issuers = rules.get("attestation_issuers") or []
        if record["issuer"] not in issuers:
            return "ATTESTATION_ISSUER_UNAUTHORIZED"
        if record["policy_version"] != rules.get("attestation_policy_version"):
            return "ATTESTATION_POLICY_MISMATCH"
        issued_at = _parse_ts(record["issued_at"])
        expires_at = _parse_ts(record["expires_at"])
        if NOW < issued_at:
            return "ATTESTATION_INVALID"
        if NOW >= expires_at:
            return "ATTESTATION_EXPIRED"
        return None

    def _encumbrance_gate(self, account: dict, amount: int):
        """available = balance - committed is the only spendable capacity."""
        if amount > account["balance"] - account["committed"]:
            return "INSUFFICIENT_COMMITMENT"
        return None

    # ------------------------------------------------------------------ #
    # internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _daily_spent(account: dict) -> int:
        cutoff = timedelta(seconds=DAILY_WINDOW_SECONDS)
        return sum(v for ts, v in account["spends"] if NOW - ts < cutoff)

    @staticmethod
    def _parse_rules(rules_json) -> dict:
        if not isinstance(rules_json, str):
            raise PpaError("INVALID_RULES")
        try:
            rules = json.loads(rules_json)
        except json.JSONDecodeError:
            raise PpaError("INVALID_RULES")
        if not isinstance(rules, dict):
            raise PpaError("INVALID_RULES")
        for key in ("daily_limit", "per_tx_limit"):
            if key in rules:
                text = rules[key]
                if (isinstance(text, bool)
                        or not isinstance(text, (str, int))
                        or not str(text).isdigit()):
                    raise PpaError("INVALID_RULES")
                rules[key] = str(int(text))
        return rules

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise PpaError("NOT_INITIALIZED")

    def _require_account(self, account_id) -> dict:
        account = self._accounts.get(account_id)
        if account is None:
            raise PpaError("UNKNOWN_ACCOUNT")
        return account


# ---------------------------------------------------------------------- #
# Vector runner (dispatch semantics mirror tools/nomos_run_vectors.py)   #
# ---------------------------------------------------------------------- #


def _coerce(value) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def run_vector(contract: Ppa, vec: dict) -> list[str]:
    failures: list[str] = []
    for i, action in enumerate(vec.get("actions", [])):
        op = action["op"]
        args = action.get("args", [])
        expect = action.get("expect")
        step = f"{vec.get('id')}#{i} {op}({', '.join(str(a) for a in args)})"
        method = getattr(contract, op, None)
        if method is None:
            failures.append(f"{step}: unknown op")
            continue

        if expect == "ok":
            try:
                method(*args)
            except Exception as exc:
                failures.append(
                    f"{step}: expected ok, raised {type(exc).__name__}: {exc}")
            continue

        if expect == "reject":
            try:
                method(*args)
            except Exception:
                continue
            failures.append(f"{step}: expected reject, but call succeeded")
            continue

        try:
            result = method(*args)
        except Exception as exc:
            failures.append(f"{step}: raised {type(exc).__name__}: {exc}")
            continue

        if isinstance(expect, dict):
            try:
                parsed = json.loads(result) if isinstance(result, str) \
                    else dict(result)
            except Exception:
                failures.append(f"{step}: expected object, got unparseable "
                                f"{result!r}")
                continue
            for key, val in expect.items():
                if _coerce(parsed.get(key)) != _coerce(val):
                    failures.append(
                        f"{step}: {key}={_coerce(parsed.get(key))}"
                        f"!={_coerce(val)}")
            continue

        if _coerce(result) != _coerce(expect):
            failures.append(f"{step}: expected {_coerce(expect)!r}, "
                            f"got {_coerce(result)!r}")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 your_build.py <vectors.json>", file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        doc = json.load(fh)
    primitive = doc.get("primitive", "ppa")
    vectors = doc.get("vectors", [])
    if not vectors:
        print(f"{primitive}: no vectors in {argv[1]}")
        return 2

    passed = 0
    total_failures: list[str] = []
    for vec in vectors:
        contract = Ppa()  # fresh contract instance per vector
        failures = run_vector(contract, vec)
        vid = vec.get("id", "?")
        if failures:
            print(f"FAIL {primitive}/{vid}")
            for f in failures:
                print(f"     {f}")
            total_failures.extend(failures)
        else:
            passed += 1
            print(f"PASS {primitive}/{vid}")

    print(f"\n{passed}/{len(vectors)} vectors passed for {primitive}")
    return 0 if not total_failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
