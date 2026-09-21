from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.transaction.entities import Channel, Transaction


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 19, 7, 0, tzinfo=UTC)


@pytest.fixture
def customer_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def recipient_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def transaction(now: datetime, customer_id: UUID, recipient_id: UUID) -> Transaction:
    return Transaction(
        uuid4(),
        customer_id,
        recipient_id,
        Decimal("30000"),
        "KZT",
        now,
        Channel.MOBILE,
        "synthetic-device-001",
    )


@pytest.fixture
def profile(now: datetime, customer_id: UUID, recipient_id: UUID) -> CustomerBehaviorProfile:
    observations = tuple(
        ProfileObservation(uuid4(), Decimal(amount), now - timedelta(days=i + 1), recipient_id)
        for i, amount in enumerate(["20000", "25000", "30000", "35000", "50000"] * 4)
    )
    return CustomerBehaviorProfile(customer_id, "KZT", now, observations)


@pytest.fixture
def native_bundle(tmp_path):
    import json

    import numpy as np
    from xgboost import XGBClassifier

    from backend.adapters.ml.bundle import ExperimentalManifest, sha256
    from backend.app.features.engine import FEATURE_NAMES

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
