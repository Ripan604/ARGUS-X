from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.domain import Experiment, physical_distance
from backend.app.replay.datasets import CounterfactualDataset
from backend.app.services.engine import ArgusEngine


@dataclass
class AdaptiveReplayRunner:
    """Execute adaptive selection against a finite, truth-sealed response bank."""

    engine: ArgusEngine
    dataset: CounterfactualDataset

    def run(self, maximum: int | None = None, *, reveal_at_end: bool = True) -> dict:
        actions = [Experiment(**item) for item in self.dataset.list_available_actions()]
        remaining = {self.engine.neo_planner._key(item): item for item in actions}
        maximum = min(maximum or self.engine.config.max_experiments, len(actions))
        trace = []
        for _ in range(maximum):
            if not remaining or self.engine.status()["should_stop"]:
                break
            plan = self.engine.neo_planner.recommend(
                self.engine.joint_state, self.engine.experiments,
                action_type="diagnostic", objective=self.engine.config.planner_objective,
                candidate_override=list(remaining.values()),
            )
            experiment = plan.selected.experiment
            signal = self.dataset.get_observation(experiment)
            result = self.engine.process_signal(signal, experiment, plan)
            remaining.pop(self.engine.neo_planner._key(experiment))
            trace.append({
                "experiment_index": result.index, "experiment": experiment.to_dict(),
                "recommendation": plan.to_dict(), "status": self.engine.status(),
            })
        report = {
            "metadata": self.dataset.get_metadata(), "trace": trace,
            "final_status": self.engine.status(), "available_action_count": len(actions),
            "selected_action_count": len(trace), "truth_was_sealed_during_execution": True,
        }
        if reveal_at_end:
            truth = self.dataset.end_blind_evaluation()
            report["revealed_truth"] = truth
            if "center_x" in truth and "center_y" in truth:
                estimate = self.engine.belief.estimate()
                report["localization_error_mm"] = float(
                    physical_distance(estimate["map_x"], estimate["map_y"], truth["center_x"], truth["center_y"], self.engine.panel) * 1_000
                )
        return report
