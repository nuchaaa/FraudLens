from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from uuid import uuid4

import pytest

from backend.adapters.events.in_memory import InMemoryEventPublisher
from backend.app.audit.entities import AuditEvent
from backend.app.features.contracts import FeatureVector
from backend.app.fraud.ports import FraudPrediction, ModelVersion
from backend.app.shared.events import DomainEvent, EventType, OutboxEvent


@pytest.mark.parametrize(
    "names,values",
    [((), ()), (("a", "a"), (1.0, 2.0)), (("a",), ()), (("a",), (float("nan"),)), (("",), (1.0,))],
)
def test_bad_feature_vectors(names, values) -> None:
    with pytest.raises(ValueError):
        FeatureVector("v1", names, values)


def test_feature_order_preserved() -> None:
    vector = FeatureVector("v1", ("amount", "new_recipient"), (30_000.0, 1.0))
    assert vector.names == ("amount", "new_recipient")
    assert vector.values == (30_000.0, 1.0)


def test_predictions_record_versions(now: datetime) -> None:
    prediction = FraudPrediction(0.8, "model-v1", "features-v1", now)
    with pytest.raises(ValueError):
        replace(prediction, probability=1.2)
    with pytest.raises(ValueError):
        replace(prediction, model_version="")


def test_model_metadata_has_no_fabricated_metrics(now: datetime) -> None:
    model = ModelVersion("model-v1", "features-v1", now, "a" * 64)
    assert model.metrics == ()
    with pytest.raises(ValueError):
        replace(model, artifact_sha256="not-a-digest")


def test_event_dispatch_and_duplicate_subscription(now: datetime) -> None:
    bus = InMemoryEventPublisher()
    received: list[DomainEvent] = []
    bus.subscribe(EventType.RISK_EVALUATED, received.append)
    bus.subscribe(EventType.RISK_EVALUATED, received.append)
    event = DomainEvent(uuid4(), EventType.RISK_EVALUATED, uuid4(), now, uuid4())
    bus.publish(event)
    assert received == [event]
    bus.publish(replace(event, event_type=EventType.PROFILE_UPDATED))
    assert received == [event]


def test_event_failure_propagates_for_retry(now: datetime) -> None:
    bus = InMemoryEventPublisher()

    def broken(event: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe(EventType.RISK_EVALUATED, broken)
    event = DomainEvent(uuid4(), EventType.RISK_EVALUATED, uuid4(), now, uuid4())
    with pytest.raises(RuntimeError, match="handler failed"):
        bus.publish(event)
    with pytest.raises(ValueError):
        OutboxEvent(event, attempts=-1)


def test_audit_is_immutable_in_memory(now: datetime) -> None:
    audit = AuditEvent(uuid4(), uuid4(), "CASE_REVIEW", uuid4(), uuid4(), now, "Synthetic test")
    with pytest.raises(FrozenInstanceError):
        audit.detail = "overwrite"  # type: ignore[misc]
