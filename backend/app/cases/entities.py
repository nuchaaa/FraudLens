from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.app.shared.validation import utc


class CaseState(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    LEGITIMATE = "LEGITIMATE"
    CLOSED = "CLOSED"


_TRANSITIONS: dict[CaseState, frozenset[CaseState]] = {
    CaseState.OPEN: frozenset({CaseState.UNDER_REVIEW}),
    CaseState.UNDER_REVIEW: frozenset({CaseState.CONFIRMED_FRAUD, CaseState.LEGITIMATE}),
    CaseState.CONFIRMED_FRAUD: frozenset({CaseState.CLOSED}),
    CaseState.LEGITIMATE: frozenset({CaseState.CLOSED}),
    CaseState.CLOSED: frozenset(),
}


class InvalidCaseTransition(ValueError):
    pass


@dataclass(frozen=True)
class CaseTransition:
    previous: CaseState
    target: CaseState
    actor_id: UUID
    timestamp: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", utc(self.timestamp))


@dataclass(frozen=True)
class FraudCase:
    case_id: UUID
    transaction_id: UUID
    assessment_id: UUID
    created_at: datetime
    history: tuple[CaseTransition, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", utc(self.created_at))
        state = CaseState.OPEN
        previous_time = self.created_at
        for transition in self.history:
            if transition.previous != state or transition.target not in _TRANSITIONS[state]:
                raise InvalidCaseTransition("invalid case history")
            if transition.timestamp < previous_time:
                raise InvalidCaseTransition("case history must be chronological")
            state, previous_time = transition.target, transition.timestamp

    @property
    def state(self) -> CaseState:
        return self.history[-1].target if self.history else CaseState.OPEN

    def transition(self, target: CaseState, actor_id: UUID, at: datetime) -> "FraudCase":
        if target not in _TRANSITIONS[self.state]:
            raise InvalidCaseTransition(f"cannot transition {self.state} to {target}")
        return replace(
            self, history=(*self.history, CaseTransition(self.state, target, actor_id, at))
        )
