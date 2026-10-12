"""Two-observation design under a declared region/Gaussian arrival-time model.

Loss is squared position error in m^2. Calibration and diagnosis share that
loss, a finite acquisition budget, and correlated velocity/timing uncertainty.
The conditional Gaussian model is exact for its linearized, region-coarsened
assumptions, not for real dispersive elastic waves. No novelty is asserted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp

from backend.app.active_learning.nuisance_design import NuisanceArrivalTimeDesign, SpatialDesignRegions, _quadrature
from backend.app.active_learning.planner import CandidateScore, PlannedExperiment
from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.models.domain import Experiment, physical_distance


def posterior_weights(prior: np.ndarray, means: np.ndarray, variances: np.ndarray, observations: np.ndarray) -> np.ndarray:
    log_joint = np.log(np.maximum(prior, np.finfo(float).tiny))[None, :] - 0.5 * (
        np.log(2 * np.pi * variances)[None, :] + (observations[:, None] - means[None, :]) ** 2 / variances[None, :])
    return np.exp(log_joint - logsumexp(log_joint, axis=1, keepdims=True))


def squared_position_risk(probabilities: np.ndarray, centers_m: np.ndarray, within_region_m2: np.ndarray) -> np.ndarray:
    """Bayes risk of the posterior mean, with unresolved within-region variance."""
    centers = centers_m - centers_m[0]  # translation invariant, avoids cancellation
    mean = probabilities @ centers
    return np.maximum(0, probabilities @ (np.sum(centers**2, axis=1) + within_region_m2) - np.sum(mean**2, axis=-1))


def expected_position_risk(prior: np.ndarray, means: np.ndarray, variances: np.ndarray,
                           centers_m: np.ndarray, within_region_m2: np.ndarray, order: int = 32) -> float:
    p, mu, var = (np.asarray(value, dtype=float) for value in (prior, means, variances))
    if p.ndim != 1 or p.size == 0 or mu.shape != p.shape or var.shape != p.shape:
        raise ValueError("Arrival model parameters must be matching nonempty vectors")
    if not all(np.isfinite(x).all() for x in (p, mu, var, centers_m, within_region_m2)) or np.any(p < 0) or p.sum() <= 0 or np.any(var <= 0):
        raise ValueError("Arrival model requires finite values, positive variance and nonnegative mass")
    if np.shape(centers_m) != (len(p), 2) or np.shape(within_region_m2) != p.shape or np.any(np.asarray(within_region_m2) < 0):
        raise ValueError("Spatial moments must match the mixture and have nonnegative variance")
    if not 8 <= order <= 128:
        raise ValueError("Risk quadrature order must be in [8, 128]")
    p = p / p.sum()
    nodes, weights = _quadrature(order)
    observations = (mu[:, None] + np.sqrt(var[:, None]) * nodes).ravel()
    posterior = posterior_weights(p, mu, var, observations)
    risks = squared_position_risk(posterior, centers_m, within_region_m2).reshape(len(p), order)
    return float(np.sum(p[:, None] * weights * risks))


@dataclass(frozen=True)
class ArrivalAction:
    experiment: Experiment
    kind: str
    means: np.ndarray
    variances: np.ndarray
    derivatives: np.ndarray


class FiniteHorizonRiskPlanner:
    """Actual observation branches; finite action bank; at most two acquisitions."""

    def __init__(self, neo_planner) -> None:
        self.neo = neo_planner
        self.config = neo_planner.config
        self.panel = neo_planner.simulator.panel
        self.arrival = NuisanceArrivalTimeDesign(self.panel, self.config.sample_rate)

    def recommend(self, state, history, *, no_go_regions=None, unavailable_actions=None,
                  candidate_override=None, calibration_override=None) -> PlannedExperiment:
        # All posterior mass contributes, including probability outside the modal cells.
        representatives = state.structural.top_hypotheses(min(8, self.config.top_hypotheses))
        regions = SpatialDesignRegions.from_posterior(state.structural.posterior, representatives, self.panel)
        p = regions.probabilities
        centers = np.column_stack([
            np.bincount(regions.membership, weights=regions.cell_probabilities * regions.coordinates_m[:, axis], minlength=len(p)) / p
            for axis in range(2)])
        within = np.bincount(regions.membership, weights=regions.cell_probabilities * np.sum(
            (regions.coordinates_m - centers[regions.membership])**2, axis=1), minlength=len(p)) / p
        prior_risk = float(squared_position_risk(p, centers, within))
        covariance = state.nuisance.propagation_covariance()
        velocity = state.nuisance.parameter("wave_velocity").mean
        timing = state.nuisance.parameter("timing_offset").mean
        actions: list[ArrivalAction] = []
        rejected = 0
        seen = set()
        for experiment in (candidate_override if candidate_override is not None else self.neo.generate_candidates(state, history)):
            key = self.neo._key(experiment)
            if key in seen:
                continue
            seen.add(key)
            if not self.neo.constraints.evaluate(experiment, no_go_regions=no_go_regions, unavailable_actions=unavailable_actions).feasible:
                rejected += 1
                continue
            analysis = self.arrival.analyze(experiment, regions, state.nuisance)
            means = np.asarray(analysis.diagnostics["arrival_means_s"])
            variance = np.asarray(analysis.diagnostics["arrival_std_s"])**2
            path = (means - timing) * velocity
            derivatives = np.column_stack((-path / velocity**2, np.ones(len(p))))
            actions.append(ArrivalAction(experiment, "diagnostic", means, variance, derivatives))
        if not actions:
            raise RuntimeError("No feasible diagnostic action remains in the risk-planning bank")

        def cost(action, previous):
            e = action.experiment
            movement = 0.0 if previous is None else float(np.hypot(e.source_x-previous.source_x, e.source_y-previous.source_y)
                                                       + np.hypot(e.receiver_x-previous.receiver_x, e.receiver_y-previous.receiver_y))
            return self.config.decision_cost_m2_per_unit * self.neo.loss.experiment_cost(movement, e.amplitude, e.duration_s)

        previous = history[-1] if history else None
        immediate = {self.neo._key(a.experiment): expected_position_risk(p, a.means, a.variances, centers, within) for a in actions}
        actions.sort(key=lambda a: immediate[self.neo._key(a.experiment)] + cost(a, previous))
        beam = actions[:self.config.planner_beam_width]
        calibrations = []
        if self.config.enable_calibration_actions:
            calibration_options = calibration_override if calibration_override is not None else [
                AdaptiveDualControlManager.calibration_experiment("direct_path", i) for i in range(3)]
            for e in calibration_options:
                if not self.neo.constraints.evaluate(e, no_go_regions=no_go_regions, unavailable_actions=unavailable_actions).feasible:
                    rejected += 1
                    continue
                distance = float(physical_distance(e.source_x, e.source_y, e.receiver_x, e.receiver_y, self.panel))
                h = np.tile([-distance / velocity**2, 1.0], (len(p), 1))
                # Same observation-noise contract as CalibrationEngine; add
                # unobserved probe pose instead of treating reference geometry as exact.
                pose_std_m = max(self.panel.width_m, self.panel.height_m) * np.hypot(
                    state.nuisance.parameter("source_pose_error").std, state.nuisance.parameter("receiver_pose_error").std)
                noise = max(1 / self.config.sample_rate, 0.00020)**2 + (pose_std_m / velocity)**2
                variance = np.full(len(p), float(h[0] @ covariance @ h[0]) + noise)
                calibrations.append(ArrivalAction(e, "calibration", np.full(len(p), timing+distance/velocity), variance, h))
        forced_calibration = state.ood_state.get("status") in {"ABSTAIN", "OUT_OF_DISTRIBUTION"} or float(state.discrepancy_state.get("model_trust", 1)) < 0.18
        if forced_calibration and not calibrations:
            raise RuntimeError("Model recovery requires calibration, but no permitted calibration action is available")
        first_actions = calibrations if forced_calibration else [*beam, *calibrations]
        horizon = min(2, self.config.max_experiments - len(history))
        if horizon < 1:
            raise RuntimeError("Measurement budget is exhausted")

        def evaluate(first: ArrivalAction, order: int) -> tuple[float, float, float]:
            after_first = expected_position_risk(p, first.means, first.variances, centers, within, order)
            if horizon == 1:
                return after_first + cost(first, previous), after_first, 0.0
            nodes, weights = _quadrature(order)
            observations = (first.means[:, None] + np.sqrt(first.variances[:, None]) * nodes).ravel()
            masses = (p[:, None] * np.broadcast_to(weights, (len(p), order))).ravel()
            posteriors = posterior_weights(p, first.means, first.variances, observations)
            total_terminal, expected_second_cost = 0.0, 0.0
            for y, mass, posterior in zip(observations, masses, posteriors):
                # Stopping after the first shot is always an admissible action.
                best_risk = float(squared_position_risk(posterior, centers, within))
                best_cost = 0.0
                for second in beam:
                    if second.experiment == first.experiment:
                        continue
                    cross = np.einsum("ij,jk,ik->i", first.derivatives, covariance, second.derivatives)
                    conditional_mean = second.means + cross / first.variances * (y-first.means)
                    conditional_variance = np.maximum(second.variances - cross**2 / first.variances, self.arrival.measurement_variance)
                    risk = expected_position_risk(posterior, conditional_mean, conditional_variance, centers, within, order)
                    second_cost = cost(second, first.experiment)
                    if risk + second_cost < best_risk + best_cost:
                        best_risk, best_cost = risk, second_cost
                total_terminal += float(mass) * best_risk
                expected_second_cost += float(mass) * best_cost
            return total_terminal + cost(first, previous) + expected_second_cost, total_terminal, expected_second_cost

        evaluated = [(action, *evaluate(action, 16)) for action in first_actions]
        evaluated.sort(key=lambda row: row[1])
        # Refine all first-action finalists rather than trusting a coarse winner.
        refined = [(action, *evaluate(action, 32)) for action, *_ in evaluated]
        refined.sort(key=lambda row: row[1])
        chosen, expected_loss, terminal_risk, second_cost = refined[0]
        coarse = {self.neo._key(a.experiment): loss for a, loss, *_ in evaluated}
        maximum_error = max(abs(loss-coarse[self.neo._key(a.experiment)]) for a, loss, *_ in refined)
        ranked_gap = refined[1][1] - expected_loss if len(refined) > 1 else float("inf")
        numerical_ambiguity = ranked_gap <= 2 * maximum_error
        kind = chosen.kind
        if kind == "diagnostic" and history and state.structural.estimate()["confidence"] >= 0.5:
            kind = "verification"
        candidates = tuple(CandidateScore(
            a.experiment, 0.0, 0.0, 0.0, cost(a, previous), 0.0, prior_risk-loss,
            expected_risk_reduction=max(0.0, prior_risk-risk), calibration_value=max(0.0, prior_risk-loss) if a.kind == "calibration" else 0,
            predicted_uncertainty_after=None, chosen_model_fidelity=0,
            reason_for_fidelity="Correlated linearized arrival-time model; no field calibration",
        ) for a, loss, risk, _ in refined)
        reason = (f"{kind.title()} minimizes modeled expected squared localization error plus acquisition cost "
                  f"over up to {horizon} measurements ({expected_loss * 1e6:.1f} mm² expected total loss).")
        diagnostics = {
            "action_type": kind, "primary_reason": reason, "calibration_type": "direct_path" if kind == "calibration" else None,
            "method": "correlated_arrival_two_step_bayes_risk_v1", "loss_units": "m^2",
            "prior_risk_m2": prior_risk, "expected_terminal_risk_m2": terminal_risk,
            "expected_total_loss_m2": expected_loss, "expected_risk_reduction": max(0.0, prior_risk-terminal_risk),
            "calibration_value": candidates[0].calibration_value,
            "expected_second_cost_m2": second_cost, "cost_m2_per_unit": self.config.decision_cost_m2_per_unit,
            "horizon": horizon, "candidate_count": len(actions), "beam_width": len(beam), "rejected_count": rejected,
            "region_count": len(p), "posterior_mass": float(p.sum()), "quadrature_orders": [16, 32],
            "maximum_quadrature_error_m2": maximum_error, "ranking_numerically_ambiguous": numerical_ambiguity,
            "forced_calibration": forced_calibration, "field_calibrated": False,
            "propagation_covariance": covariance.tolist(),
            "assumptions": ["first_order_velocity_timing", "conditional_region_position_independence",
                            "independent_measurement_and_pose_noise", "finite_candidate_beam", "one_dominant_scatterer"],
            "alternatives": [{"action_type": a.kind, "experiment": a.experiment.to_dict(),
                              "expected_total_loss_m2": loss, "terminal_risk_m2": risk} for a, loss, risk, _ in refined],
        }
        return PlannedExperiment(candidates[0], candidates[:5], reason, strategy="finite_horizon_bayes_risk",
                                 action_type=kind, objective="BAYES_RISK", structured_explanation=diagnostics,
                                 chosen_model_fidelity=0, reason_for_fidelity=candidates[0].reason_for_fidelity,
                                 planning_horizon=horizon)
