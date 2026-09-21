import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from xgboost import XGBClassifier

from backend.adapters.features.artifacts import write_context
from backend.adapters.ml.__main__ import main
from backend.adapters.ml.bundle import ArtifactError, ExperimentalManifest, checked_bytes, sha256
from backend.adapters.ml.xgboost_model import ExperimentalXGBoostModel
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.engine import FEATURE_NAMES, extract_features
from backend.app.fraud.ports import FraudModel
from backend.app.fraud.service import predict_experimental_context
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.transaction.entities import Transaction
from ml.src.training import export_model


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, str, XGBClassifier]:
    rng = np.random.default_rng(17)
    x = rng.normal(size=(40, 29))
    model = XGBClassifier(n_estimators=3, max_depth=2, n_jobs=1, random_state=17)
    model.fit(x, np.asarray([0, 1] * 20))
    from importlib.metadata import version

    report = {
        "status": "complete",
        "experiment_version": "synthetic-comparison-v1",
        "generator_version": "synthetic-behavior-v1",
        "feature_version": "behavior-v1",
        "feature_names": FEATURE_NAMES,
        "source_sha256": "a" * 64,
        "lock_sha256": "b" * 64,
        "seed": 17,
        "selected_model": "xgboost",
        "synthetic_only": True,
        "production_eligible": False,
        "artifacts": {"selected.joblib": "c" * 64},
        "packages": {"xgboost": version("xgboost")},
    }
    raw_report = json.dumps(report).encode()
    native = bytes(model.get_booster().save_raw(raw_format="ubj"))
    manifest = ExperimentalManifest.model_validate(
        {
            "model_version": f"experimental-xgb-{sha256(native)}",
            "model_sha256": sha256(native),
            "feature_names": FEATURE_NAMES,
            "training_report_sha256": sha256(raw_report),
            "training_dataset_sha256": "a" * 64,
            "training_lock_sha256": "b" * 64,
            "original_pickle_sha256": "c" * 64,
            "seed": 17,
            "xgboost_version": version("xgboost"),
            "exported_at": datetime.now(UTC),
        }
    )
    path = tmp_path / "bundle"
    path.mkdir()
    (path / "manifest.json").write_text(manifest.model_dump_json())
    (path / "model.ubj").write_bytes(native)
    (path / "training-report.json").write_bytes(raw_report)
    return path, sha256((path / "manifest.json").read_bytes()), model


@pytest.fixture
def context(transaction: Transaction, profile: CustomerBehaviorProfile) -> FeatureContext:
    return FeatureContext(
        uuid4(),
        transaction,
        replace(profile, timezone="UTC"),
        "UTC",
        (),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )


def test_port_native_parity_and_real_versions(
    bundle: tuple[Path, str, XGBClassifier], context: FeatureContext
) -> None:
    path, pin, original = bundle
    adapter = ExperimentalXGBoostModel(path, expected_manifest_sha256=pin)
    port: FraudModel = adapter
    features = extract_features(context)
    result = predict_experimental_context(port, context)
    expected = float(original.predict_proba(np.asarray([features.values]))[0, 1])
    assert result.probability == pytest.approx(expected, abs=1e-7)
    assert result.model_version == adapter.manifest.model_version
    assert result.feature_version == "behavior-v1"
    assert result.timestamp >= context.captured_at
    assert adapter.manifest.trained_at is None
    assert adapter.manifest.production_eligible is False


@pytest.mark.parametrize("target", ["manifest.json", "model.ubj", "training-report.json"])
def test_corruption_rejected_before_native_load(
    bundle: tuple[Path, str, XGBClassifier], target: str
) -> None:
    path, pin, _ = bundle
    with (path / target).open("ab") as file:
        file.write(b"broken")
    with pytest.raises(ArtifactError, match="digest"):
        ExperimentalXGBoostModel(path, expected_manifest_sha256=pin)


@pytest.mark.parametrize(
    "change",
    ["production", "order", "version", "clock", "unknown", "runtime", "provenance", "identifier"],
)
def test_manifest_incompatibilities(bundle: tuple[Path, str, XGBClassifier], change: str) -> None:
    path, _, _ = bundle
    data = json.loads((path / "manifest.json").read_text())
    if change == "production":
        data["production_eligible"] = True
    elif change == "order":
        data["feature_names"].reverse()
    elif change == "version":
        data["feature_version"] = "ulb-pca-v1"
    elif change == "clock":
        data["exported_at"] = "2026-09-21T01:00:00"
    elif change == "unknown":
        data["unused"] = 1
    elif change == "runtime":
        data["xgboost_version"] = "0.0.0"
    elif change == "provenance":
        data["training_dataset_sha256"] = "d" * 64
    else:
        data["model_version"] = "invented"
    raw = json.dumps(data).encode()
    (path / "manifest.json").write_bytes(raw)
    with pytest.raises(ValueError):
        ExperimentalXGBoostModel(path, expected_manifest_sha256=sha256(raw))


def test_scope_and_feature_mismatch(
    bundle: tuple[Path, str, XGBClassifier], context: FeatureContext
) -> None:
    path, pin, _ = bundle
    adapter = ExperimentalXGBoostModel(path, expected_manifest_sha256=pin)
    vector = extract_features(context)
    for invalid in (
        replace(vector, version="other"),
        replace(vector, names=tuple(reversed(vector.names))),
    ):
        with pytest.raises(ArtifactError):
            adapter.predict(invalid)
    for invalid_context in (
        replace(context, customer_timezone="Asia/Almaty"),
        replace(context, profile=None, candidate=replace(context.candidate, currency="USD")),
        replace(context, profile=replace(context.profile, short_window_days=15)),
    ):
        with pytest.raises(ValueError):
            predict_experimental_context(adapter, invalid_context)


def test_cli_replay_and_fail_closed(
    bundle: tuple[Path, str, XGBClassifier],
    context: FeatureContext,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, pin, _ = bundle
    artifact = tmp_path / "context.json"
    write_context(artifact, context)
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", "invalid")
    monkeypatch.setenv("FRAUDLENS_API_PRINCIPALS", "invalid")
    args = ["--bundle", str(path), "--manifest-sha256", pin, "--context", str(artifact)]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["production_eligible"] is False and result["calibrated"] is False
    assert 0 <= result["uncalibrated_score"] <= 1
    (path / "model.ubj").unlink()
    assert main(args) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_export_never_unpickles_unreviewed_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "report.json").write_text("{}")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("untrusted pickle reached deserializer")

    monkeypatch.setattr(export_model.joblib, "load", forbidden)
    with pytest.raises(ArtifactError):
        export_model.export(tmp_path, tmp_path / "out", seed=17)
    with pytest.raises(ArtifactError):
        export_model.export(tmp_path, tmp_path / "out", seed=99)
    with pytest.raises(ArtifactError, match="size"):
        checked_bytes(tmp_path / "report.json", "0" * 64, 1)


@pytest.mark.parametrize("scores", [[float("nan")], [1.5], [0.1, 0.2]])
def test_invalid_model_outputs_fail(
    bundle: tuple[Path, str, XGBClassifier],
    context: FeatureContext,
    monkeypatch: pytest.MonkeyPatch,
    scores: list[float],
) -> None:
    path, pin, _ = bundle
    adapter = ExperimentalXGBoostModel(path, expected_manifest_sha256=pin)
    monkeypatch.setattr(adapter._booster, "predict", lambda *a, **k: np.asarray(scores))
    with pytest.raises(ValueError):
        adapter.predict(extract_features(context))


def test_prediction_clock_cannot_precede_capture(
    bundle: tuple[Path, str, XGBClassifier], context: FeatureContext
) -> None:
    from datetime import timedelta

    path, pin, _ = bundle
    adapter = ExperimentalXGBoostModel(
        path, expected_manifest_sha256=pin, clock=lambda: context.captured_at - timedelta(seconds=1)
    )
    with pytest.raises(ValueError, match="precede"):
        predict_experimental_context(adapter, context)


def test_wrong_model_shape_rejected(bundle: tuple[Path, str, XGBClassifier]) -> None:
    path, _, _ = bundle
    model = XGBClassifier(n_estimators=1, n_jobs=1)
    model.fit(np.asarray([[0, 0], [1, 1]]), np.asarray([0, 1]))
    raw = bytes(model.get_booster().save_raw(raw_format="ubj"))
    manifest = json.loads((path / "manifest.json").read_text())
    manifest.update(model_sha256=sha256(raw), model_version=f"experimental-xgb-{sha256(raw)}")
    document = json.dumps(manifest).encode()
    (path / "manifest.json").write_bytes(document)
    (path / "model.ubj").write_bytes(raw)
    with pytest.raises(ArtifactError, match="shape"):
        ExperimentalXGBoostModel(path, expected_manifest_sha256=sha256(document))


def test_wrong_pickle_hash_cannot_reach_deserializer(
    bundle: tuple[Path, str, XGBClassifier], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _ = bundle
    report = (path / "training-report.json").read_bytes()
    (path / "report.json").write_bytes(report)
    (path / "selected.joblib").write_bytes(b"untrusted pickle")
    monkeypatch.setattr(export_model, "REVIEWED_REPORTS", {17: sha256(report)})

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("untrusted pickle reached deserializer")

    monkeypatch.setattr(export_model.joblib, "load", forbidden)
    with pytest.raises(ArtifactError, match="digest"):
        export_model.export(path, path / "output", seed=17)


def test_export_known_fixture_and_refuse_overwrite(
    bundle: tuple[Path, str, XGBClassifier], monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    import joblib

    path, _, model = bundle
    payload = io.BytesIO()
    joblib.dump(model, payload)
    raw_model = payload.getvalue()
    prepared = json.dumps([{"values": [float(i)] * 29} for i in range(4)]).encode()
    report = json.loads((path / "training-report.json").read_text())
    report["artifacts"] = {"selected.joblib": sha256(raw_model), "prepared.json": sha256(prepared)}
    raw_report = json.dumps(report).encode()
    (path / "report.json").write_bytes(raw_report)
    (path / "selected.joblib").write_bytes(raw_model)
    (path / "prepared.json").write_bytes(prepared)
    monkeypatch.setattr(export_model, "REVIEWED_REPORTS", {17: sha256(raw_report)})
    pin = export_model.export(path, path / "exported", seed=17)
    ExperimentalXGBoostModel(path / "exported", expected_manifest_sha256=pin)
    assert json.loads((path / "exported" / "parity.json").read_text())["rows"] == 4
    with pytest.raises(FileExistsError):
        export_model.export(path, path / "exported", seed=17)


@pytest.mark.parametrize("kind", ["list", "nested", "incomplete"])
def test_invalid_report_structure(bundle: tuple[Path, str, XGBClassifier], kind: str) -> None:
    path, _, _ = bundle
    report = json.loads((path / "training-report.json").read_text())
    if kind == "list":
        report = []
    elif kind == "nested":
        report["packages"] = []
    else:
        report["status"] = "failed"
    raw_report = json.dumps(report).encode()
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["training_report_sha256"] = sha256(raw_report)
    document = json.dumps(manifest).encode()
    (path / "training-report.json").write_bytes(raw_report)
    (path / "manifest.json").write_bytes(document)
    with pytest.raises(ArtifactError):
        ExperimentalXGBoostModel(path, expected_manifest_sha256=sha256(document))
