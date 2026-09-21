"""Read-only experimental captured-context inference; not an assessment or verdict."""

from backend.app.features.context import FeatureContext, FeatureInputError
from backend.app.features.engine import extract_features
from backend.app.fraud.ports import FraudModel, FraudPrediction


def predict_experimental_context(model: FraudModel, context: FeatureContext) -> FraudPrediction:
    # The exported synthetic artifacts were trained only under this declared scope.
    if context.candidate.currency != "KZT" or context.customer_timezone != "UTC":
        raise FeatureInputError("experimental model scope is KZT with UTC profile policy")
    if context.profile is not None and (
        context.profile.timezone != "UTC"
        or context.profile.long_window_days != 180
        or context.profile.short_window_days != 30
    ):
        raise FeatureInputError("experimental model requires the original profile window policy")
    result = model.predict(extract_features(context))
    if result.feature_version != context.feature_version:
        raise FeatureInputError("prediction feature version mismatch")
    if result.timestamp < context.captured_at:
        raise FeatureInputError("prediction cannot precede captured input availability")
    return result
