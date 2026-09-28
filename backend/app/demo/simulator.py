"""Deterministic, database-free scenario simulation using production domain code.

Authored labels are an offline oracle for controlled behavior tests, never analyst
feedback, verified bank evidence, or permission to persist profile admissions.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from uuid import UUID, uuid5

from backend.app.features.context import ContextSource, FeatureContext
from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.profile.gate import ProfileUpdateGate
from backend.app.risk.sequence_policy import decide_sequence_risk
from backend.app.risk.service import RiskPolicy, Strategy, evaluate_risk
from backend.app.sequence.engine import SequenceStatus, evaluate_sequence
from backend.app.transaction.entities import Channel, Transaction

VERSION = "controlled-scenarios-v1"
ANCHOR = datetime(2026, 9, 20, 9, tzinfo=UTC)
_NAMESPACE = UUID("4bf4971b-76c1-4993-8983-b14e66559e4f")
_NORMAL_AMOUNTS = ("22000", "31000", "28000", "35000", "26000", "33000", "29000")
_NORMAL_PURPOSES = (
    ("known", "Household transfer"),
    ("groceries", "Grocery purchase"),
    ("utilities", "Monthly utility payment"),
)


def _id(label: str) -> UUID:
    return uuid5(_NAMESPACE, f"{VERSION}/{label}")


def _fixed_time(value: datetime) -> datetime:
    return value


@dataclass(frozen=True)
class SimulatedTransaction:
    transaction: Transaction
    scenario: str
    authored_label: str
    purpose: str


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario: str
    transaction_id: UUID
    authored_label: str
    risk_status: str
    risk_level: str | None
    suggested_action: str | None
    rule_score: float | None
    matched_rules: tuple[str, ...]
    matched_sequences: tuple[str, ...]
    rule_reasons: tuple[str, ...]
    sequence_reasons: tuple[str, ...]
    risk_v2_status: str
    risk_v2_level: str | None
    risk_v2_action: str | None
    risk_v2_source: str
    risk_v2_policy_sha256: str
    unavailable_sequences: tuple[str, ...]
    profile_version_before: int
    profile_version_after: int
    median_before: Decimal
    median_after: Decimal
    short_median_before: Decimal | None
    short_median_after: Decimal | None
    gate_action: str


@dataclass(frozen=True)
class Simulation:
    rows: tuple[SimulatedTransaction, ...]
    outcomes: tuple[ScenarioOutcome, ...]


def build_simulation() -> Simulation:
    """Run authored cases against the real pure feature/risk/sequence/gate engines."""
    rows: list[SimulatedTransaction] = []
    activity: dict[UUID, list[Transaction]] = {}
    profiles: dict[UUID, CustomerBehaviorProfile] = {}
    owners = tuple(_id(f"customer/{index:02d}") for index in range(10))

    for index, owner in enumerate(owners):
        history: list[Transaction] = []
        for step in range(200):
            amount = _NORMAL_AMOUNTS[(step + index) % len(_NORMAL_AMOUNTS)]
            recipient, purpose = _NORMAL_PURPOSES[step % len(_NORMAL_PURPOSES)]
            timestamp = ANCHOR - timedelta(days=100 - step // 2) + timedelta(hours=step % 2)
            tx = Transaction(
                _id(f"history/{index:02d}/{step:03d}"),
                owner,
                _id(f"recipient/{index:02d}/{recipient}"),
                Decimal(amount),
                "KZT",
                timestamp,
                Channel.MOBILE,
                f"sim-device-{index:02d}",
            )
            history.append(tx)
            rows.append(SimulatedTransaction(tx, "BASELINE", "AUTHORED_NORMAL", purpose))
        activity[owner] = history
        # The pure simulation assumes an oracle-approved subset. No database review,
        # profile revision, or production workflow is created by this assumption.
        profiles[owner] = CustomerBehaviorProfile(
            owner,
            "KZT",
            ANCHOR - timedelta(minutes=1),
            tuple(
                ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, tx.recipient_id)
                for tx in history[-100:]
            ),
            timezone="Asia/Almaty",
            admission_workflow_verified=True,
            admission_policy_version="simulated-oracle-only-v1",
            learning_decision_id=_id(f"oracle/{index:02d}"),
        )

    candidates: list[SimulatedTransaction] = []

    def candidate(
        scenario: str,
        owner_index: int,
        step: int,
        amount: str,
        timestamp: datetime,
        recipient: str,
        device: str,
        label: str,
        purpose: str,
        channel: Channel = Channel.MOBILE,
    ) -> None:
        candidates.append(
            SimulatedTransaction(
                Transaction(
                    _id(f"candidate/{scenario}/{step:02d}"),
                    owners[owner_index],
                    _id(f"recipient/{owner_index:02d}/{recipient}"),
                    Decimal(amount),
                    "KZT",
                    timestamp,
                    channel,
                    device,
                ),
                scenario,
                label,
                purpose,
            )
        )

    candidate(
        "A",
        0,
        0,
        "25000",
        ANCHOR,
        "known",
        "sim-device-00",
        "AUTHORED_LEGITIMATE",
        "Ordinary household transfer",
    )
    candidate(
        "B",
        1,
        0,
        "8000000",
        ANCHOR,
        "vehicle-dealer",
        "sim-device-01",
        "AUTHORED_LEGITIMATE",
        "One-off vehicle purchase",
        Channel.BRANCH,
    )
    candidate(
        "C",
        1,
        0,
        "500000",
        ANCHOR + timedelta(days=1, hours=13),
        "new",
        "new-device",
        "AUTHORED_FRAUD",
        "New recipient after vehicle purchase",
    )
    for step in range(30):
        amount_value = 45000 + (65000 * step // 29)
        candidate(
            "D",
            2,
            step,
            str(amount_value),
            ANCHOR + timedelta(days=1 + 2 * step),
            "known",
            "sim-device-02",
            "AUTHORED_LEGITIMATE",
            "Gradually increasing course instalment",
        )
    for step in range(6):
        candidate(
            "E",
            3,
            step,
            "25000",
            ANCHOR + timedelta(days=1, minutes=10 * step),
            "new",
            "sim-device-03",
            "AUTHORED_FRAUD",
            "Repeated low-value transfer to new recipient",
        )

    gate = ProfileUpdateGate()
    outcomes: list[ScenarioOutcome] = []
    for row in sorted(
        candidates,
        key=lambda item: (item.transaction.timestamp, str(item.transaction.transaction_id)),
    ):
        tx = row.transaction
        profile = profiles[tx.customer_id]
        previous = tuple(item for item in activity[tx.customer_id] if item.timestamp < tx.timestamp)
        context = FeatureContext(
            _id(f"context/{tx.transaction_id}"),
            tx,
            profile,
            "Asia/Almaty",
            previous,
            tx.timestamp,
            ContextSource.DECLARED_OFFLINE,
        )
        risk = evaluate_risk(
            context, RiskPolicy(Strategy.RULES_ONLY), clock=partial(_fixed_time, tx.timestamp)
        )
        sequence = evaluate_sequence(context)
        risk_v2 = decide_sequence_risk(risk, sequence)
        verdict = AnalystVerdict.LEGITIMATE if row.authored_label == "AUTHORED_LEGITIMATE" else None
        decision, updated = gate.apply(tx, profile, verdict)
        before = profile.long_term
        after = updated.long_term
        short_before = profile.short_term
        short_after = updated.short_term
        assert before is not None and after is not None
        outcomes.append(
            ScenarioOutcome(
                row.scenario,
                tx.transaction_id,
                row.authored_label,
                risk.status,
                risk.level.value if risk.level else None,
                risk.suggested_action.value if risk.suggested_action else None,
                risk.rule_score,
                tuple(item.code for item in risk.rules.outcomes if item.status.value == "MATCHED"),
                tuple(
                    item.code for item in sequence.outcomes if item.status == SequenceStatus.MATCHED
                ),
                tuple(reason.message for reason in risk.rules.reasons),
                tuple(reason.message for reason in sequence.reasons),
                risk_v2.status,
                risk_v2.level.value if risk_v2.level else None,
                risk_v2.suggested_action.value if risk_v2.suggested_action else None,
                risk_v2.decision_source,
                risk_v2.policy_sha256,
                risk_v2.unavailable_sequences,
                profile.version,
                updated.version,
                before.median,
                after.median,
                short_before.median if short_before else None,
                short_after.median if short_after else None,
                decision.action.value,
            )
        )
        profiles[tx.customer_id] = updated
        activity[tx.customer_id].append(tx)
        rows.append(row)
    return Simulation(tuple(rows), tuple(outcomes))
