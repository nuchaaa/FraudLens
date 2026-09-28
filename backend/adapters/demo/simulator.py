"""Export the controlled Phase 16 simulator without touching PostgreSQL."""

import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path

from backend.app.demo.simulator import Simulation, build_simulation


def _csv(fieldnames: tuple[str, ...], records: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def export_documents(simulation: Simulation) -> dict[str, str]:
    """Return stable file contents; expectations remain distinct from observations."""
    rows = simulation.rows
    transactions = [
        {
            "transaction_id": str(row.transaction.transaction_id),
            "customer_id": str(row.transaction.customer_id),
            "recipient_id": str(row.transaction.recipient_id),
            "amount": str(row.transaction.amount),
            "currency": row.transaction.currency,
            "timestamp": row.transaction.timestamp.isoformat(),
            "device_id": row.transaction.device_id,
            "channel": row.transaction.channel.value,
            "scenario": row.scenario,
            "authored_label": row.authored_label,
            "purpose": row.purpose,
        }
        for row in rows
    ]
    customers = sorted({str(row.transaction.customer_id) for row in rows})
    recipients = sorted({str(row.transaction.recipient_id) for row in rows})
    outcomes = simulation.outcomes
    candidate_by_id = {
        row.transaction.transaction_id: row for row in rows if row.scenario != "BASELINE"
    }
    by_scenario = {
        scenario: [item for item in outcomes if item.scenario == scenario] for scenario in "ABCDE"
    }
    a, b, c = (by_scenario[key][0] for key in "ABC")
    d, e = by_scenario["D"], by_scenario["E"]
    checks = {
        "A_normal_low_allow_accept": a.risk_v2_level == "LOW"
        and a.risk_v2_action == "ALLOW"
        and a.gate_action == "ACCEPT",
        "B_exceptional_review_and_quarantine": b.risk_v2_level in {"MEDIUM", "HIGH", "CRITICAL"}
        and b.risk_v2_action != "ALLOW"
        and b.gate_action == "QUARANTINE"
        and b.median_before == b.median_after,
        "C_remains_suspicious_after_B": c.risk_v2_level in {"HIGH", "CRITICAL"}
        and c.gate_action == "QUARANTINE"
        and c.median_before == b.median_before,
        "D_gradual_adaptation": all(item.gate_action == "ACCEPT" for item in d)
        and d[-1].short_median_after is not None
        and d[0].short_median_before is not None
        and d[-1].short_median_after > d[0].short_median_before,
        "E_low_value_attack_risk_flags": any(
            item.risk_v2_level in {"MEDIUM", "HIGH", "CRITICAL"} for item in e
        ),
        "E_sequence_detects_and_profile_resists": any(item.matched_sequences for item in e)
        and all(item.gate_action == "QUARANTINE" for item in e)
        and e[-1].median_after == e[0].median_before,
    }
    manifest = {
        "version": "controlled-results-v2",
        "transaction_fixture_version": "controlled-scenarios-v1",
        "synthetic_only": True,
        "production_eligible": False,
        "labels": (
            "authored oracle for offline controlled tests; not analyst feedback or real fraud truth"
        ),
        "profile_assumption": (
            "Each customer has 200 raw prior transactions. The last 100 are assumed "
            "oracle-approved solely in memory to exercise behavior code. This is not a "
            "verified review workflow or a persisted profile."
        ),
        "risk_policy": (
            "risk-v2-sequence-experimental review floor over unchanged risk-v1 rules_only; "
            "uncalibrated authored thresholds; no new probability"
        ),
        "counts": {
            "customers": len(customers),
            "baseline_transactions": sum(row.scenario == "BASELINE" for row in rows),
            "scenario_transactions": len(outcomes),
            "by_scenario": dict(sorted(Counter(item.scenario for item in outcomes).items())),
        },
        "authored_expectations": {
            "A": {"risk": "LOW", "action": "ALLOW", "profile_update": "ACCEPT"},
            "B": {
                "risk": "MEDIUM_OR_HIGHER",
                "action": "REVIEW",
                "profile_update": "QUARANTINE_AFTER_ASSUMED_LEGITIMATE",
            },
            "C": {
                "risk": "HIGH_OR_CRITICAL",
                "action": "REVIEW",
                "profile_update": "QUARANTINE_WITHOUT_VERIFIED_VERDICT",
                "baseline": "UNCHANGED_AFTER_B",
            },
            "D": {"profile_update": "ORDERED_ACCEPT", "short_median": "INCREASES"},
            "E": {
                "risk": "MEDIUM_OR_HIGHER",
                "sequence": "MATCHES",
                "profile_update": "QUARANTINE_WITHOUT_VERIFIED_VERDICT",
            },
        },
        "checks": checks,
        "legacy_observations": {
            "E_risk_v1_gap_retained": all(item.risk_level == "LOW" for item in e)
        },
        "outcomes": [
            {
                "scenario": item.scenario,
                "transaction_id": str(item.transaction_id),
                "customer_id": str(candidate_by_id[item.transaction_id].transaction.customer_id),
                "amount": str(candidate_by_id[item.transaction_id].transaction.amount),
                "currency": candidate_by_id[item.transaction_id].transaction.currency,
                "timestamp": candidate_by_id[item.transaction_id].transaction.timestamp.isoformat(),
                "purpose": candidate_by_id[item.transaction_id].purpose,
                "authored_label": item.authored_label,
                "risk_status": item.risk_status,
                "risk_level": item.risk_level,
                "suggested_action": item.suggested_action,
                "rule_score": item.rule_score,
                "matched_rules": item.matched_rules,
                "matched_sequences": item.matched_sequences,
                "rule_reasons": item.rule_reasons,
                "sequence_reasons": item.sequence_reasons,
                "risk_v2_status": item.risk_v2_status,
                "risk_v2_level": item.risk_v2_level,
                "risk_v2_action": item.risk_v2_action,
                "risk_v2_source": item.risk_v2_source,
                "risk_v2_policy_sha256": item.risk_v2_policy_sha256,
                "unavailable_sequences": item.unavailable_sequences,
                "profile_version_before": item.profile_version_before,
                "profile_version_after": item.profile_version_after,
                "median_before": str(item.median_before),
                "median_after": str(item.median_after),
                "short_median_before": str(item.short_median_before)
                if item.short_median_before is not None
                else None,
                "short_median_after": str(item.short_median_after)
                if item.short_median_after is not None
                else None,
                "gate_action": item.gate_action,
            }
            for item in outcomes
        ],
        "limitations": (
            "Rules-v1 excludes sequence matches and still says LOW/ALLOW on E. The separate "
            "risk-v2 review floor raises an evaluable sequence match to at least MEDIUM "
            "without changing a score or asserting a probability. This authored policy "
            "is uncalibrated and is not wired into durable evaluation. No database, analyst "
            "decision, model training, or real-world metric is created."
        ),
    }
    return {
        "customers.csv": _csv(
            ("customer_id", "display_name"),
            [
                {"customer_id": value, "display_name": f"Synthetic Customer {index:02d}"}
                for index, value in enumerate(customers)
            ],
        ),
        "recipients.csv": _csv(
            ("recipient_id", "display_name"),
            [
                {"recipient_id": value, "display_name": f"Synthetic Recipient {index:02d}"}
                for index, value in enumerate(recipients)
            ],
        ),
        "transactions.csv": _csv(tuple(transactions[0]), transactions),
        "scenario_manifest.json": json.dumps(manifest, sort_keys=True, indent=2) + "\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="Directory for deterministic files"
    )
    parser.add_argument(
        "--replace", action="store_true", help="Replace existing generated files in the output"
    )
    args = parser.parse_args()
    output: Path = args.output
    documents = export_documents(build_simulation())
    output.mkdir(parents=True, exist_ok=True)
    for name, content in documents.items():
        target = output / name
        if target.exists() and target.read_text(encoding="utf-8") != content and not args.replace:
            raise SystemExit(f"refusing to overwrite changed file: {target}")
        target.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "checks": json.loads(documents["scenario_manifest.json"])["checks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
