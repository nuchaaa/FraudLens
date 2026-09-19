from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from backend.app.cases.entities import CaseState, CaseTransition, FraudCase, InvalidCaseTransition


def make_case(now: datetime, state: CaseState) -> FraudCase:
    case = FraudCase(uuid4(), uuid4(), uuid4(), now)
    if state == CaseState.OPEN:
        return case
    case = case.transition(CaseState.UNDER_REVIEW, uuid4(), now)
    if state == CaseState.UNDER_REVIEW:
        return case
    case = case.transition(
        CaseState.LEGITIMATE if state == CaseState.LEGITIMATE else CaseState.CONFIRMED_FRAUD,
        uuid4(),
        now,
    )
    return case.transition(CaseState.CLOSED, uuid4(), now) if state == CaseState.CLOSED else case


@pytest.mark.parametrize("source", list(CaseState))
@pytest.mark.parametrize("target", list(CaseState))
def test_complete_transition_matrix(now: datetime, source: CaseState, target: CaseState) -> None:
    allowed = {
        (CaseState.OPEN, CaseState.UNDER_REVIEW),
        (CaseState.UNDER_REVIEW, CaseState.LEGITIMATE),
        (CaseState.UNDER_REVIEW, CaseState.CONFIRMED_FRAUD),
        (CaseState.LEGITIMATE, CaseState.CLOSED),
        (CaseState.CONFIRMED_FRAUD, CaseState.CLOSED),
    }
    case = make_case(now, source)
    if (source, target) in allowed:
        updated = case.transition(target, uuid4(), now)
        assert updated.state == target
        assert case.state == source
        assert len(updated.history) == len(case.history) + 1
    else:
        with pytest.raises(InvalidCaseTransition):
            case.transition(target, uuid4(), now)


def test_backdated_and_forged_history_rejected(now: datetime) -> None:
    case = make_case(now, CaseState.OPEN)
    with pytest.raises(InvalidCaseTransition, match="chronological"):
        case.transition(CaseState.UNDER_REVIEW, uuid4(), now - timedelta(seconds=1))
    forged = CaseTransition(CaseState.OPEN, CaseState.CLOSED, uuid4(), now)
    with pytest.raises(InvalidCaseTransition, match="history"):
        replace(case, history=(forged,))
