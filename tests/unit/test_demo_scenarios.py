"""The demo story is fixed, synthetic and contains no claimed risk result."""

from collections import Counter
from datetime import timedelta
from decimal import Decimal

from backend.app.demo.scenarios import ANCHOR, build_plan, demo_id
from backend.app.demo.stages import (
    STAGES,
    fixture_bootstrap_trace_matches,
    predecessor,
    stage_events,
)


def test_manifest_is_stable_and_covers_five_stories() -> None:
    first, second = build_plan(), build_plan()
    assert first.document() == second.document()
    assert first.sha256() == second.sha256()
    assert len(first.customers) == 4
    assert len(first.events) == 62
    assert Counter(event.scenario for event in first.events) == {
        "A": 13,
        "BC": 12,
        "B": 1,
        "C": 1,
        "D": 17,
        "E": 18,
    }
    assert first.document()["synthetic_only"] is True
    assert first.document()["production_eligible"] is False
    assert len({event.transaction.transaction_id for event in first.events}) == 62
    assert all(event.transaction.currency == "KZT" for event in first.events)
    assert all(event.transaction.timestamp <= ANCHOR + timedelta(days=5) for event in first.events)
    owners = {
        scenario: {
            event.transaction.customer_id for event in first.events if event.scenario == scenario
        }
        for scenario in ("A", "BC", "B", "C", "D", "E")
    }
    assert all(len(customer_ids) == 1 for customer_ids in owners.values())
    assert owners["BC"] == owners["B"] == owners["C"]
    assert len({next(iter(owners[scenario])) for scenario in ("A", "B", "D", "E")}) == 4


def test_vehicle_and_followup_share_customer_without_changing_baseline_facts() -> None:
    plan = build_plan()
    vehicle = next(event.transaction for event in plan.events if event.scenario == "B")
    followup = next(event.transaction for event in plan.events if event.scenario == "C")
    baseline = [
        event.transaction
        for event in plan.events
        if event.scenario == "BC" and event.transaction.customer_id == vehicle.customer_id
    ]
    assert vehicle.amount == Decimal("8000000")
    assert followup.amount == Decimal("500000")
    assert followup.customer_id == vehicle.customer_id
    assert followup.recipient_id != vehicle.recipient_id
    assert all(item.amount <= Decimal("40000") for item in baseline)
    assert all(item.timestamp < vehicle.timestamp < followup.timestamp for item in baseline)


def test_ladder_and_gradual_change_have_declared_amounts() -> None:
    plan = build_plan()
    for scenario, expected in (
        ("D", [45000, 60000, 75000, 90000, 110000]),
        ("E", [50000, 70000, 100000, 150000, 250000, 500000]),
    ):
        current = [
            event.transaction.amount
            for event in plan.events
            if event.scenario == scenario and event.story != "unreviewed normal-looking history"
        ]
        assert current == [Decimal(value) for value in expected]


def test_stages_partition_the_unchanged_manifest() -> None:
    plan = build_plan()
    assert len(STAGES) == 15
    assert len(stage_events(plan, "BASELINE")) == 48
    assert {
        event.transaction.transaction_id for stage in STAGES for event in stage_events(plan, stage)
    } == {event.transaction.transaction_id for event in plan.events}
    assert [len(stage_events(plan, stage)) for stage in STAGES[1:]] == [1] * 14
    assert predecessor("C") == "B"
    assert predecessor("D5") == "D4"
    assert predecessor("E6") == "E5"
    assert predecessor("A") is None


def test_bootstrap_trace_requires_matching_fixture_admissions_and_distinct_reviewers() -> None:
    plan = build_plan()
    baseline = stage_events(plan, "BASELINE")
    owner = next(event.transaction.customer_id for event in plan.events if event.scenario == "B")
    ids = frozenset(
        event.transaction.transaction_id
        for event in baseline
        if event.transaction.customer_id == owner
    )
    selected = tuple(sorted(ids, key=str)[:5])
    first, second = demo_id("test/reviewer-1"), demo_id("test/reviewer-2")
    evidence = tuple(
        (tx_id, first if index < 3 else second) for index, tx_id in enumerate(selected)
    )
    assert fixture_bootstrap_trace_matches(ids, selected, evidence)
    assert not fixture_bootstrap_trace_matches(ids, selected[:4], evidence)
    assert not fixture_bootstrap_trace_matches(
        ids, selected, ((tx_id, first) for tx_id in selected)
    )
    unrelated = next(
        event.transaction.transaction_id for event in baseline if event.scenario == "A"
    )
    assert not fixture_bootstrap_trace_matches(
        ids, (*selected[:4], unrelated), (*evidence[:4], (unrelated, second))
    )
