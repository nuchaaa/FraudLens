"""Human-readable guide over retained demo evidence, without verdict inference."""

from collections.abc import Mapping
from typing import cast

from backend.app.demo.scenarios import DemoPlan


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError("invalid demo evidence report")
    return cast("Mapping[str, object]", value)


def _items(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValueError("invalid demo evidence report")
    return [_mapping(item) for item in value]


def _next_step(fact: object, evaluations: list[Mapping[str, object]], stage: str) -> str:
    if fact == "CONFLICT":
        return "STOP: fixture UUID has different stored facts."
    if fact == "ABSENT":
        return (
            f"On a disposable local test DB, run --check-stage {stage}; apply only if READY. "
            "Do not bypass required review/profile evidence."
        )
    if not evaluations:
        return "Capture an experimental evaluation with an explicit pre-decision profile version."
    cases = [case for evaluation in evaluations for case in _items(evaluation["cases"])]
    if not cases:
        return "If independent review is warranted, open a case for a retained evaluation."
    if any(not _items(case["feedback"]) for case in cases):
        return "Await an authenticated analyst's independent review; do not infer a verdict."
    return "Inspect recorded review and separate learning evidence before making a claim."


def render_walkthrough(plan: DemoPlan, report: Mapping[str, object]) -> str:
    """Present only recorded status and explicit manual actions for A-E."""
    if (
        report.get("version") != "demo-evidence-v1"
        or report.get("manifest_sha256") != plan.sha256()
    ):
        raise ValueError("demo evidence report does not match the fixture manifest")
    recorded = {str(item["transaction_id"]): item for item in _items(report.get("events"))}
    profiles = {str(item["customer_id"]): item for item in _items(report.get("profiles"))}
    counts = _mapping(report.get("fixture_fact_counts"))
    lines = [
        "# FraudLens local five-story walkthrough",
        "",
        f"Manifest SHA-256: `{plan.sha256()}`",
        f"Fixture facts: {counts.get('MATCH', 0)} matching, "
        f"{counts.get('ABSENT', 0)} absent, {counts.get('CONFLICT', 0)} conflicting.",
        "Synthetic, experimental, production-ineligible. Story text is not a verdict.",
    ]
    for scenario, title, requirement in (
        (
            "A",
            "Normal-looking transfer",
            "Inspect cold/insufficient evidence; quiet rules do not prove legitimacy.",
        ),
        (
            "B",
            "Exceptional vehicle payment",
            "First establish a BC baseline from independently reviewed earlier cases; "
            "inspect the actual gate decision before claiming preservation.",
        ),
        (
            "C",
            "Later new-recipient transfer",
            "Pin the BC version retained before this decision and compare it with B's "
            "recorded learning decision; do not assume historical availability.",
        ),
        (
            "D",
            "Gradual amount change",
            "Only independently reviewed, separately authorized accepted steps can "
            "advance a profile; inspect revisions in event order.",
        ),
        (
            "E",
            "Escalating transfer sequence",
            "Inspect retained rule/sequence evidence and reviews; authored attack "
            "text is not a fraud label.",
        ),
    ):
        lines.extend(("", f"## {scenario} — {title}"))
        candidates = [
            event
            for event in plan.events
            if event.scenario == scenario and event.story != "unreviewed normal-looking history"
        ]
        owner = str(candidates[0].transaction.customer_id)
        profile = profiles.get(owner)
        if profile is None:
            raise ValueError("demo evidence report omits a customer profile summary")
        lines.append(
            f"Customer `{owner}`; current KZT profile version: "
            f"{profile['current_version']}; committed revisions: "
            f"{len(_items(profile['revisions']))}."
        )
        lines.append(f"Evidence requirement: {requirement}")
        for index, event in enumerate(candidates, start=1):
            identifier = str(event.transaction.transaction_id)
            entry = recorded.get(identifier)
            if entry is None:
                raise ValueError("demo evidence report omits a candidate")
            evaluations = _items(entry["evaluations"])
            cases = [case for evaluation in evaluations for case in _items(evaluation["cases"])]
            lines.append(f"- `{identifier}`: fixture {entry['fixture_fact']}.")
            lines.append(
                "  Recorded evaluations: "
                + (
                    ", ".join(
                        f"{item['risk_status']} (profile v{item['captured_profile_version']})"
                        for item in evaluations
                    )
                    if evaluations
                    else "none"
                )
                + "."
            )
            revisions = entry["prior_profile_revisions"]
            if not isinstance(revisions, list):
                raise ValueError("invalid demo evidence report")
            lines.append(
                "  Event-time-compatible profile revisions: "
                f"{', '.join(str(version) for version in revisions) if revisions else 'none'} "
                "(historical availability unverified)."
            )
            lines.append(
                f"  Recorded cases: {len(cases)}; "
                f"feedback records: {sum(len(_items(case['feedback'])) for case in cases)}; "
                f"learning decisions: {sum(len(_items(case['learning'])) for case in cases)}."
            )
            stage = scenario if scenario in {"A", "B", "C"} else f"{scenario}{index}"
            lines.append(f"  Next: {_next_step(entry['fixture_fact'], evaluations, stage)}")
    lines.extend(
        (
            "",
            "This walkthrough does not certify B/C baseline preservation or D adaptation. "
            "Inspect independent review and recorded profile-learning decisions.",
            "A matching event-time profile revision does not prove historical availability; "
            "use the version retained in the original evaluation.",
            "No banking action or profile admission is performed by this report.",
        )
    )
    return "\n".join(lines) + "\n"
