"""Independent falsification cases are stable and do not establish calibration."""

import json
from pathlib import Path

from ml.src.evaluation.sequence_challenge import run_challenges


def test_challenge_report_exposes_false_review_and_missed_spaced_attack() -> None:
    report = run_challenges()
    cases = {item["name"]: item for item in report["cases"]}
    assert report == run_challenges()
    assert report["calibrated"] is report["production_eligible"] is False
    assert report["labels_verified"] is False
    assert len(cases) == 7

    # A benign household batch triggers the same review floor as the authored
    # attack. The risk policy cannot infer intent from these available facts.
    assert cases["household_batch"]["risk_v2_action"] == "STEP_UP_VERIFICATION"
    benign = cases["new_payee_benign_batch"]
    attack = cases["new_payee_attack_batch"]
    assert benign["authored_intent"] != attack["authored_intent"]
    for field in ("risk_v1_level", "risk_v2_level", "risk_v2_action", "matched_sequences"):
        assert benign[field] == attack[field]

    # A spaced sequence falls outside the authored 24-hour window and is not
    # rescued by this floor. This is an intentional negative finding.
    assert cases["spaced_new_payee"]["risk_v2_action"] == "ALLOW"
    assert cases["spaced_new_payee"]["matched_sequences"] == []
    assert cases["no_verified_baseline"]["risk_v2_source"] == "ABSTAIN"
    assert len(cases["no_verified_baseline"]["unavailable_sequences"]) == 4
    assert cases["large_purchase"]["risk_v2_source"] == "RISK_V1"


def test_committed_challenge_report_replays_exactly() -> None:
    root = Path(__file__).resolve().parents[2]
    saved = (root / "ml/experiments/sequence-challenge-v1/report.json").read_text()
    assert saved == json.dumps(run_challenges(), indent=2, sort_keys=True) + "\n"
