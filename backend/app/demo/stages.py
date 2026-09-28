"""Deterministic fixture stages; no review or trust assertions."""

from collections.abc import Iterable
from uuid import UUID

from backend.app.demo.scenarios import DemoEvent, DemoPlan
from backend.app.profile.learning import MINIMUM_BOOTSTRAP_OBSERVATIONS, MINIMUM_BOOTSTRAP_REVIEWERS

STAGES = (
    "BASELINE",
    "A",
    "B",
    "C",
    *(f"D{index}" for index in range(1, 6)),
    *(f"E{index}" for index in range(1, 7)),
)


def stage_events(plan: DemoPlan, stage: str) -> tuple[DemoEvent, ...]:
    """Select original manifest facts without changing IDs or its digest."""
    if stage not in STAGES:
        raise ValueError("unknown demo stage")
    if stage == "BASELINE":
        return tuple(
            event for event in plan.events if event.story == "unreviewed normal-looking history"
        )
    scenario = stage[0]
    candidates = tuple(
        event
        for event in plan.events
        if event.scenario == scenario and event.story != "unreviewed normal-looking history"
    )
    return candidates[int(stage[1:]) - 1 : int(stage[1:])] if len(stage) > 1 else candidates


def predecessor(stage: str) -> str | None:
    """Same-customer previous candidate that must already have retained evidence."""
    if stage == "C":
        return "B"
    if stage.startswith(("D", "E")) and len(stage) > 1 and int(stage[1:]) > 1:
        return f"{stage[0]}{int(stage[1:]) - 1}"
    return None


def fixture_bootstrap_trace_matches(
    baseline_ids: frozenset[UUID],
    admitted_ids: Iterable[UUID],
    evidence: Iterable[tuple[UUID, UUID]],
) -> bool:
    """Require bootstrap evidence and admissions for the same fixture facts."""
    admitted = set(admitted_ids) & baseline_ids
    supported = [(tx_id, reviewer_id) for tx_id, reviewer_id in evidence if tx_id in admitted]
    return (
        len({tx_id for tx_id, _ in supported}) >= MINIMUM_BOOTSTRAP_OBSERVATIONS
        and len({reviewer_id for _, reviewer_id in supported}) >= MINIMUM_BOOTSTRAP_REVIEWERS
    )
