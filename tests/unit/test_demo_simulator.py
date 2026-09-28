"""Controlled expectations, including a deliberately visible risk-v1 failure."""

import csv
import io
import json
from collections import Counter

from backend.adapters.demo.simulator import export_documents
from backend.app.demo.simulator import build_simulation


def test_controlled_scenarios_exercise_real_pure_engines() -> None:
    simulation = build_simulation()
    assert len(simulation.rows) == 2039
    assert Counter(row.scenario for row in simulation.rows)["BASELINE"] == 2000
    assert len({row.transaction.customer_id for row in simulation.rows}) == 10
    assert len({row.transaction.transaction_id for row in simulation.rows}) == 2039
    a, b, c = (
        next(item for item in simulation.outcomes if item.scenario == scenario)
        for scenario in "ABC"
    )
    d = [item for item in simulation.outcomes if item.scenario == "D"]
    e = [item for item in simulation.outcomes if item.scenario == "E"]

    assert (a.risk_level, a.suggested_action, a.gate_action) == ("LOW", "ALLOW", "ACCEPT")
    assert (b.risk_level, b.suggested_action, b.gate_action) == (
        "MEDIUM",
        "STEP_UP_VERIFICATION",
        "QUARANTINE",
    )
    assert b.median_after == b.median_before
    assert (c.risk_level, c.suggested_action, c.gate_action) == (
        "HIGH",
        "HOLD_AND_REVIEW",
        "QUARANTINE",
    )
    assert c.profile_version_before == b.profile_version_before
    assert c.median_before == b.median_before
    assert len(d) == 30 and all(item.gate_action == "ACCEPT" for item in d)
    assert d[0].short_median_before == 29000
    assert d[-1].short_median_after == 94310
    assert len(e) == 6 and all(item.gate_action == "QUARANTINE" for item in e)
    assert "CUMULATIVE_LOW_VALUE_SEQUENCE" in e[-1].matched_sequences
    # The detector gap must stay visible: supplemental sequence evidence does not
    # currently contribute to risk-v1's LOW/ALLOW suggestion.
    assert e[-1].risk_level == "LOW"
    assert e[-1].suggested_action == "ALLOW"


def test_export_is_deterministic_and_discloses_failed_expectation() -> None:
    first = export_documents(build_simulation())
    assert first == export_documents(build_simulation())
    rows = list(csv.DictReader(io.StringIO(first["transactions.csv"])))
    assert len(rows) == 2039
    assert {row["currency"] for row in rows} == {"KZT"}
    assert len({row["purpose"] for row in rows if row["scenario"] == "BASELINE"}) == 3
    b = next(row for row in rows if row["scenario"] == "B")
    c = next(row for row in rows if row["scenario"] == "C")
    assert b["customer_id"] == c["customer_id"]
    assert b["recipient_id"] != c["recipient_id"]
    assert b["device_id"] != c["device_id"]
    manifest = json.loads(first["scenario_manifest.json"])
    assert manifest["synthetic_only"] is True
    assert manifest["production_eligible"] is False
    assert manifest["authored_expectations"]["E"]["risk"] == "MEDIUM_OR_HIGHER"
    assert manifest["checks"]["C_remains_suspicious_after_B"] is True
    assert manifest["checks"]["D_gradual_adaptation"] is True
    assert manifest["checks"]["E_low_value_attack_risk_flags"] is False
