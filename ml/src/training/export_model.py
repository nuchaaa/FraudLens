"""Restricted one-time conversion of the three reviewed Phase 7 local artifacts."""

import argparse
import io
import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from xgboost import Booster, DMatrix, XGBClassifier

from backend.adapters.ml.bundle import (
    MAX_METADATA_BYTES,
    MAX_MODEL_BYTES,
    ArtifactError,
    ExperimentalManifest,
    checked_bytes,
    sha256,
)
from backend.app.features.engine import FEATURE_NAMES

# Independent reviewed digests, not values supplied by a neighboring untrusted file.
REVIEWED_REPORTS = {
    17: "75240cee00bcf180d028b45216fdba35d328cef8ece8aa587a95a58ffec8ccff",
    29: "a818c00a32416dde9f705df300766e698cc8d4de142e01b7a3a6d8a0cb1e3298",
    43: "e334ae3598c81290ce390f15de98984f0ff7ded9054d11b77a28d5fed46fbb0c",
}


def export(run: Path, output: Path, *, seed: int) -> str:
    if seed not in REVIEWED_REPORTS:
        raise ArtifactError("unreviewed training run")
    report_bytes = checked_bytes(run / "report.json", REVIEWED_REPORTS[seed], MAX_METADATA_BYTES)
    report = json.loads(report_bytes)
    if (
        report["selected_model"] != "xgboost"
        or report["seed"] != seed
        or report["feature_version"] != "behavior-v1"
        or tuple(report["feature_names"]) != FEATURE_NAMES
        or report["synthetic_only"] is not True
        or report["production_eligible"] is not False
    ):
        raise ArtifactError("unsupported training report")
    if version("xgboost") != report["packages"]["xgboost"]:
        raise ArtifactError("conversion requires original XGBoost runtime")
    model_bytes = checked_bytes(
        run / "selected.joblib", report["artifacts"]["selected.joblib"], MAX_MODEL_BYTES
    )
    prepared_bytes = checked_bytes(
        run / "prepared.json", report["artifacts"]["prepared.json"], 64 * 1024 * 1024
    )
    # Only the reviewed bytes are deserialized; no reread/path race after digest checking.
    model = joblib.load(io.BytesIO(model_bytes))
    if type(model) is not XGBClassifier or model.n_features_in_ != len(FEATURE_NAMES):
        raise ArtifactError("unsupported model class/shape")
    if model.classes_.tolist() != [0, 1]:
        raise ArtifactError("unsupported class order")
    native = bytes(model.get_booster().save_raw(raw_format="ubj"))
    restored = Booster(params={"nthread": 1})
    restored.load_model(bytearray(native))
    rows = json.loads(prepared_bytes)
    x = np.asarray([row["values"] for row in rows], dtype=np.float64)
    expected = np.asarray(model.predict_proba(x)[:, 1], dtype=np.float64)
    actual = np.asarray(restored.predict(DMatrix(x)), dtype=np.float64)
    if not np.isfinite(actual).all() or not np.allclose(actual, expected, rtol=0, atol=1e-7):
        raise ArtifactError("native conversion parity failed")
    model_digest = sha256(native)
    manifest = ExperimentalManifest.model_validate(
        {
            "model_version": f"experimental-xgb-{model_digest}",
            "model_sha256": model_digest,
            "feature_names": FEATURE_NAMES,
            "training_report_sha256": sha256(report_bytes),
            "training_dataset_sha256": report["source_sha256"],
            "training_lock_sha256": report["lock_sha256"],
            "original_pickle_sha256": report["artifacts"]["selected.joblib"],
            "xgboost_version": report["packages"]["xgboost"],
            "seed": seed,
            "exported_at": datetime.now(UTC),
        }
    )
    document = manifest.model_dump_json(indent=2).encode()
    output.mkdir(parents=True, exist_ok=False)
    (output / "model.ubj").write_bytes(native)
    (output / "training-report.json").write_bytes(report_bytes)
    (output / "parity.json").write_text(
        json.dumps(
            {
                "rows": len(rows),
                "max_absolute_score_difference": float(np.max(np.abs(actual - expected))),
                "absolute_tolerance": 1e-7,
                "synthetic_only": True,
            },
            indent=2,
        )
        + "\n"
    )
    # Write the manifest last; failed exports are not loadable bundles.
    (output / "manifest.json").write_bytes(document)
    return sha256(document)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export reviewed synthetic XGBoost artifacts only")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=sorted(REVIEWED_REPORTS), required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "manifest_sha256": export(args.run, args.output, seed=args.seed),
                "production_eligible": False,
            }
        )
    )


if __name__ == "__main__":
    main()
