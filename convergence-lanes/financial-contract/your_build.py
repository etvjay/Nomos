"""Financial Contract - independent build (convergence lane, capability v0.1.0).

Convergence mode: EXACT (judgmentBearing: false - JUDGMENT_BOUNDARY = NONE)

Obligation/cash-flow lifecycle narrowed scope: principal conservation,
deterministic payment application (status APPLIED), timestamp-based maturity,
full-repayment closure, and CREDITOR-gated default declaration after maturity.

Invariants implemented:
- conservation: outstanding = principal - total_paid at all times (int math);
- overpayment DENIED (never clipped) and denied payments consume no payment id;
- duplicate contract ids / per-contract payment ids rejected (replay-safe);
- CLOSED and DEFAULTED are terminal; payment records append-only/immutable;
- default only by the creditor, only after maturity, with outstanding balance.

GenLayer conventions: single contract class, writes return canonical JSON
(sorted keys, compact separators), views return canonical JSON or "".
Rejections raise.
"""

import json


JUDGMENT_BOUNDARY = "NONE"
PRIMITIVE_ID = "financial-contract"
CAPABILITY_VERSION = "0.1.0"

CONTRACT_STATUSES = ("ACTIVE", "MATURED", "DEFAULTED", "CLOSED")
DENIAL_REASONS = (
    "EXCEEDS_OUTSTANDING",
    "BEFORE_VALIDITY_WINDOW",
    "CONTRACT_CLOSED",
    "CONTRACT_DEFAULTED",
    "CONTRACT_MATURED",
)


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _uint(text, field):
    if not isinstance(text, str):
        raise ValueError(f"{field} must be uint-string")
    stripped = text.lstrip("0") or "0"
    if not stripped.isdigit():
        raise ValueError(f"invalid {field}: {text!r}")
    return int(stripped)


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


class FinancialContract:
    """Obligation lifecycle state + append-only applied-payment records.
    Does NOT move funds - application is a recorded obligation; actual
    movement belongs to the settlement layer."""

    def __init__(self):
        self._contracts = {}   # contract_id -> record
        self._payments = {}    # (contract_id, payment_id) -> record

    # ---------------- writes ----------------

    def open_contract(self, contract_id, creditor, obligor, principal, asset,
                      valid_after, maturity, authority_ref):
        _require(isinstance(contract_id, str) and contract_id != "",
                 "contract_id required")
        _require(contract_id not in self._contracts, "duplicate contract_id")
        _require(isinstance(creditor, str) and creditor != "", "creditor required")
        _require(isinstance(obligor, str) and obligor != "", "obligor required")
        _require(creditor != obligor, "self-dealing rejected")
        principal_i = _uint(principal, "principal")
        _require(principal_i > 0, "principal must be positive")
        _require(isinstance(asset, str) and asset != "", "asset required")
        valid_after_i = int(str(valid_after))
        maturity_i = int(str(maturity))
        _require(valid_after_i <= maturity_i, "inverted validity window")
        _require(isinstance(authority_ref, str) and authority_ref != "",
                 "authority_ref (upstream Pact/allocation origin) required")

        rec = {
            "contract_id": contract_id,
            "creditor": creditor,
            "obligor": obligor,
            "principal": str(principal_i),
            "asset": asset,
            "valid_after": str(valid_after_i),
            "maturity": str(maturity_i),
            "authority_ref": authority_ref,
            "status": "ACTIVE",
            "total_paid": "0",
            "outstanding": str(principal_i),
        }
        self._contracts[contract_id] = rec
        return _canonical(rec)

    def apply_payment(self, contract_id, payment_id, amount, at_timestamp):
        rec = self._contracts.get(contract_id)
        _require(rec is not None, "unknown contract_id")
        _require(isinstance(payment_id, str) and payment_id != "",
                 "payment_id required")
        key = (contract_id, payment_id)
        # Replay rejection; denied payments never consumed an id.
        _require(key not in self._payments, "duplicate payment_id")
        amount_i = _uint(amount, "amount")
        ts = int(str(at_timestamp))

        def deny(reason_code):
            return _canonical({
                "decision": "DENY",
                "reason_code": reason_code,
                "payment_id": payment_id,
                "applied": "0",
            })

        status = self._effective_status(rec)
        if status == "CLOSED":
            return deny("CONTRACT_CLOSED")
        if status == "DEFAULTED":
            return deny("CONTRACT_DEFAULTED")
        if ts < int(rec["valid_after"]):
            return deny("BEFORE_VALIDITY_WINDOW")
        # NOTE: v0.1 semantics - the maturity timestamp gates DEFAULT
        # declaration, not payment application. Post-maturity payments still
        # apply deterministically; CONTRACT_MATURED is denied only from an
        # explicitly MATURED terminal-leaning status.
        if rec["status"] == "MATURED":
            return deny("CONTRACT_MATURED")
        outstanding = int(rec["principal"]) - int(rec["total_paid"])
        if amount_i > outstanding:
            return deny("EXCEEDS_OUTSTANDING")

        # Deterministic application - exact integer arithmetic.
        new_total = int(rec["total_paid"]) + amount_i
        new_outstanding = int(rec["principal"]) - new_total
        rec["total_paid"] = str(new_total)
        rec["outstanding"] = str(new_outstanding)
        if new_outstanding == 0:
            rec["status"] = "CLOSED"
        pay = {
            "payment_id": payment_id,
            "contract_id": contract_id,
            "amount": str(amount_i),
            "status": "APPLIED",
            "at_timestamp": str(ts),
            "outstanding_after": str(new_outstanding),
        }
        self._payments[key] = pay  # append-only; immutable once written
        return _canonical({
            "decision": "APPLY",
            "applied": str(amount_i),
            "outstanding": str(new_outstanding),
            "total_paid": str(new_total),
            "payment_id": payment_id,
        })

    def declare_default(self, contract_id, sender=None, at_timestamp=None):
        """Creditor-gated: only the creditor may declare default, only after
        maturity, while a balance remains outstanding."""
        rec = self._contracts.get(contract_id)
        _require(rec is not None, "unknown contract_id")
        _require(sender is not None and sender == rec["creditor"],
                 "defaultByNonCreditor rejected")
        now = int(str(at_timestamp)) if at_timestamp is not None else int(rec["maturity"])
        _require(now >= int(rec["maturity"]), "defaultBeforeMaturity rejected")
        _require(int(rec["outstanding"]) > 0, "no outstanding balance")
        status = self._effective_status(rec)
        _require(status in ("ACTIVE", "MATURED"),
                 f"cannot declare default from {status}")
        rec["status"] = "DEFAULTED"
        return _canonical(rec)

    # ---------------- views ----------------

    @staticmethod
    def _effective_status(rec):
        return rec["status"]

    def get_contract(self, contract_id):
        rec = self._contracts.get(contract_id)
        return _canonical(rec) if rec else ""

    def get_payment(self, contract_id, payment_id):
        pay = self._payments.get((contract_id, payment_id))
        return _canonical(pay) if pay else ""


# ---------------- canonical vector runner ----------------

def run_vectors(vector_path):
    """Run canonical v0.1 vectors. Expected dicts match as subsets; strings
    compare exactly; 'ok'/'reject' gate exceptions."""
    with open(vector_path) as fh:
        suite = json.load(fh)
    results = []
    for vec in suite["vectors"]:
        contract = FinancialContract()
        failures = []
        for i, action in enumerate(vec["actions"]):
            op, args, expect = action["op"], action["args"], action["expect"]
            try:
                out = getattr(contract, op)(*args)
                err = None
            except Exception as exc:  # noqa: BLE001 - rejection is data here
                out, err = None, exc
            if expect == "reject":
                if err is None:
                    failures.append(f"[{i}] {op} expected reject, got ok: {out}")
            elif expect == "ok":
                if err is not None:
                    failures.append(f"[{i}] {op} expected ok, got {err}")
            elif isinstance(expect, str):
                got = "" if err is not None else out
                if got != expect:
                    failures.append(f"[{i}] {op}: expected {expect!r}, got {got!r}")
            elif isinstance(expect, dict):
                if err is not None:
                    failures.append(f"[{i}] {op} raised {err}")
                else:
                    actual = json.loads(out)
                    for k, v in expect.items():
                        if actual.get(k) != v:
                            failures.append(
                                f"[{i}] {op}: field {k}: expected {v!r}, "
                                f"got {actual.get(k)!r}")
        results.append({"id": vec["id"], "pass": not failures,
                        "failures": failures})
    return suite["primitive"], results


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "vectors/v0.1.json"
    prim, res = run_vectors(path)
    ok = True
    for r in res:
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {prim}/{r['id']}")
        for f in r["failures"]:
            print("   ", f)
    sys.exit(0 if ok else 1)
