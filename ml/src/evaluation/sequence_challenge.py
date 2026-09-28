"""Independent, synthetic falsification cases for the experimental sequence floor.

These cases are deliberately separate from the Phase 16 A--E generator. Their
authored intents are hypotheses, not observed fraud labels or calibration data.
"""

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from backend.app.features.context import ContextSource, FeatureContext
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.risk.sequence_policy import decide_sequence_risk
from backend.app.risk.service import RiskPolicy, Strategy, evaluate_risk
from backend.app.sequence.engine import evaluate_sequence
from backend.app.transaction.entities import Channel, Transaction

VERSION = "sequence-challenge-v1"
ANCHOR = datetime(2026, 10, 1, 12, tzinfo=UTC)
NAMESPACE = UUID("31aee229-7300-4f11-9b4d-b888c75ac6c7")


def _id(value: str) -> UUID:
    return uuid5(NAMESPACE, f"{VERSION}/{value}")


@dataclass(frozen=True)
class Challenge:
    name: str
    authored_intent: str
    amounts: tuple[str, ...]
    minutes_before_candidate: tuple[int, ...]
    recipient: str
    trusted_profile: bool = True


CHALLENGES = (
    Challenge("single_known", "AUTHORED_BENIGN", ("25000",), (), "known"),
    Challenge(
        "household_batch",
        "AUTHORED_BENIGN",
        ("25000", "25000", "25000", "25000"),
        (30, 20, 10),
        "known",
    ),
    Challenge(
        "new_payee_benign_batch",
        "AUTHORED_BENIGN",
        ("25000", "25000", "25000", "25000"),
        (30, 20, 10),
        "new",
    ),
    Challenge(
        "new_payee_attack_batch",
        "AUTHORED_ATTACK",
        ("25000", "25000", "25000", "25000"),
        (30, 20, 10),
        "new",
    ),
    Challenge(
        "spaced_new_payee",
        "AUTHORED_ATTACK",
        ("25000", "25000", "25000", "25000"),
        (75 * 60, 50 * 60, 25 * 60),
        "new",
    ),
    Challenge("large_purchase", "AUTHORED_BENIGN", ("8000000",), (), "new"),
    Challenge(
        "no_verified_baseline",
        "UNKNOWN",
        ("25000", "25000", "25000", "25000"),
        (30, 20, 10),
        "new",
        False,
    ),
)


def _challenge_context(challenge: Challenge) -> FeatureContext:
    owner = _id(f"owner/{challenge.name}")
    known = _id(f"recipient/{challenge.name}/known")
    recipient = known if challenge.recipient == "known" else _id(f"recipient/{challenge.name}/new")
    baseline = tuple(
        Transaction(
            _id(f"baseline/{challenge.name}/{index}"),
            owner,
            known,
            Decimal("30000"),
            "KZT",
            ANCHOR - timedelta(days=index + 1),
            Channel.MOBILE,
            "challenge-device",
        )
        for index in range(20)
    )
    profile = (
        CustomerBehaviorProfile(
            owner,
            "KZT",
            ANCHOR - timedelta(minutes=1),
            tuple(
                ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, known)
                for tx in baseline
            ),
            admission_workflow_verified=True,
            admission_policy_version="authored-oracle-only",
            learning_decision_id=_id(f"assumed-approval/{challenge.name}"),
        )
        if challenge.trusted_profile
        else None
    )
    recent = tuple(
        Transaction(
            _id(f"recent/{challenge.name}/{index}"),
            owner,
            recipient,
            Decimal(challenge.amounts[index]),
            "KZT",
            ANCHOR - timedelta(minutes=minutes),
            Channel.MOBILE,
            "challenge-device",
        )
        for index, minutes in enumerate(challenge.minutes_before_candidate)
    )
    candidate = Transaction(
        _id(f"candidate/{challenge.name}"),
        owner,
        recipient,
        Decimal(challenge.amounts[-1]),
        "KZT",
        ANCHOR,
        Channel.MOBILE,
        "challenge-device",
    )
    return FeatureContext(
        _id(f"context/{challenge.name}"),
        candidate,
        profile,
        "Asia/Almaty",
        (*baseline, *recent),
        ANCHOR,
        ContextSource.DECLARED_OFFLINE,
    )


def run_challenges() -> dict[str, object]:
    """Evaluate independent authored cases without learning or database access."""
    cases: list[dict[str, object]] = []
    for challenge in CHALLENGES:
        context = _challenge_context(challenge)
        base = evaluate_risk(context, RiskPolicy(Strategy.RULES_ONLY), clock=lambda: ANCHOR)
        sequence = evaluate_sequence(context)
        updated = decide_sequence_risk(base, sequence)
        cases.append(
            {
                "name": challenge.name,
                "authored_intent": challenge.authored_intent,
                "risk_v1_level": base.level.value if base.level else None,
                "risk_v1_action": base.suggested_action.value if base.suggested_action else None,
                "risk_v2_level": updated.level.value if updated.level else None,
                "risk_v2_action": updated.suggested_action.value
                if updated.suggested_action
                else None,
                "risk_v2_source": updated.decision_source,
                "matched_sequences": list(updated.matched_sequences),
                "unavailable_sequences": list(updated.unavailable_sequences),
            }
        )
    return {
        "version": VERSION,
        "synthetic_only": True,
        "calibrated": False,
        "production_eligible": False,
        "labels_verified": False,
        "limitation": (
            "Authored intents are not independent fraud labels. This is a falsification "
            "exercise, not operating-point selection or real-world performance."
        ),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline sequence-policy challenge report")
    parser.add_argument("--output", type=Path, help="New JSON path; never overwrites evidence")
    args = parser.parse_args()
    document = json.dumps(run_challenges(), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(document, end="")
    else:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(document)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "sha256": hashlib.sha256(document.encode()).hexdigest(),
                }
            )
        )


if __name__ == "__main__":
    main()
