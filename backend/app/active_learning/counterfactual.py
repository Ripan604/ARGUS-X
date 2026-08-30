from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.digital_twin.forward_models import ForwardModel, ForwardPrediction
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment


@dataclass(frozen=True)
class HypothesisPrediction:
    hypothesis: dict
    probability: float
    prediction: ForwardPrediction

    def to_dict(self) -> dict:
        return {
            "hypothesis": self.hypothesis,
            "probability": self.probability,
            "prediction": self.prediction.to_dict(),
        }


@dataclass(frozen=True)
class CounterfactualAnalysis:
    predictions: tuple[HypothesisPrediction, ...]
    jensen_shannon: float
    bhattacharyya: float
    symmetric_kl: float
    predictive_variance_separation: float
    worst_case_separation: float
    most_separated_pair: tuple[int, int]

    @property
    def combined_separation(self) -> float:
        return float(np.clip(0.34 * self.jensen_shannon + 0.32 * self.bhattacharyya + 0.20 * self.predictive_variance_separation + 0.14 * self.worst_case_separation, 0, 1))

    def to_dict(self) -> dict:
        return {
            "predictions": [item.to_dict() for item in self.predictions],
            "jensen_shannon": self.jensen_shannon,
            "bhattacharyya": self.bhattacharyya,
            "symmetric_kl": self.symmetric_kl,
            "predictive_variance_separation": self.predictive_variance_separation,
            "worst_case_separation": self.worst_case_separation,
            "combined_separation": self.combined_separation,
            "most_separated_pair": list(self.most_separated_pair),
        }


def _pair_metrics(a: ForwardPrediction, b: ForwardPrediction) -> tuple[float, float, float, float]:
    mean_delta = a.mean - b.mean
    covariance_a = np.diag(a.covariance) + 1e-9
    covariance_b = np.diag(b.covariance) + 1e-9
    average = 0.5 * (covariance_a + covariance_b)
    mahalanobis = float(np.sum(mean_delta**2 / average))
    bhattacharyya_distance = 0.125 * mahalanobis + 0.5 * float(np.sum(np.log(average / np.sqrt(covariance_a * covariance_b))))
    bhattacharyya = float(1 - np.exp(-max(0.0, bhattacharyya_distance)))
    kl_ab = 0.5 * float(np.sum(covariance_a / covariance_b + mean_delta**2 / covariance_b - 1 + np.log(covariance_b / covariance_a)))
    kl_ba = 0.5 * float(np.sum(covariance_b / covariance_a + mean_delta**2 / covariance_a - 1 + np.log(covariance_a / covariance_b)))
    symmetric_kl = max(0.0, 0.5 * (kl_ab + kl_ba))
    js_approx = float(1 - np.exp(-0.25 * symmetric_kl))
    variance_separation = float(1 - np.exp(-0.5 * mahalanobis))
    return js_approx, bhattacharyya, symmetric_kl, variance_separation


class CounterfactualExperimentEngine:
    def analyze(
        self,
        experiment: Experiment,
        hypotheses: list[dict],
        nuisance: NuisancePosterior,
        model: ForwardModel,
    ) -> CounterfactualAnalysis:
        predictions = tuple(
            HypothesisPrediction(hypothesis, float(hypothesis["probability"]), model.predict(experiment, hypothesis, nuisance))
            for hypothesis in hypotheses
        )
        if len(predictions) < 2:
            return CounterfactualAnalysis(predictions, 0.0, 0.0, 0.0, 0.0, 0.0, (0, 0))
        js_values, bh_values, kl_values, variance_values, weighted_values = [], [], [], [], []
        pairs: list[tuple[int, int]] = []
        for left in range(len(predictions)):
            for right in range(left + 1, len(predictions)):
                metrics = _pair_metrics(predictions[left].prediction, predictions[right].prediction)
                weight = predictions[left].probability * predictions[right].probability
                js_values.append(metrics[0]); bh_values.append(metrics[1]); kl_values.append(metrics[2]); variance_values.append(metrics[3])
                weighted_values.append(weight * (0.5 * metrics[0] + 0.5 * metrics[1]))
                pairs.append((left, right))
        pair_weight_sum = sum(predictions[left].probability * predictions[right].probability for left, right in pairs) + 1e-12
        most = int(np.argmax(weighted_values))
        return CounterfactualAnalysis(
            predictions,
            float(sum(predictions[left].probability * predictions[right].probability * js for (left, right), js in zip(pairs, js_values)) / pair_weight_sum),
            float(sum(predictions[left].probability * predictions[right].probability * bh for (left, right), bh in zip(pairs, bh_values)) / pair_weight_sum),
            float(sum(predictions[left].probability * predictions[right].probability * kl for (left, right), kl in zip(pairs, kl_values)) / pair_weight_sum),
            float(sum(predictions[left].probability * predictions[right].probability * value for (left, right), value in zip(pairs, variance_values)) / pair_weight_sum),
            float(min(js_values)),
            pairs[most],
        )

