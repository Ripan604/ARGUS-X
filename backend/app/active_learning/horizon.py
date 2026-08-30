from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.active_learning.planner import CandidateScore


@dataclass(frozen=True)
class HorizonScore:
    immediate: float
    future: float
    route_cost: float
    total: float
    horizon: int


class RecedingHorizonPlanner:
    """Small beam rollout approximation; intentionally not a full POMDP."""

    def rerank(self, candidates: list[CandidateScore], horizon: int, beam_width: int) -> tuple[list[CandidateScore], dict[int, HorizonScore]]:
        horizon = int(np.clip(horizon, 1, 3))
        if horizon == 1 or len(candidates) < 2:
            return candidates, {id(item): HorizonScore(item.final_score, 0.0, 0.0, item.final_score, 1) for item in candidates}
        beam = candidates[: max(2, beam_width)]
        scores: dict[int, HorizonScore] = {}
        for candidate in candidates:
            future_options = []
            for future in beam:
                if future is candidate:
                    continue
                route = float(np.hypot(candidate.experiment.source_x - future.experiment.source_x, candidate.experiment.source_y - future.experiment.source_y))
                diversity = 1.0 - candidate.repetition_penalty * future.repetition_penalty
                future_options.append(0.62 * future.final_score * diversity - 0.12 * route)
            future_value = max(future_options, default=0.0)
            if horizon == 3:
                future_value *= 1.28
            total = candidate.final_score + future_value
            scores[id(candidate)] = HorizonScore(candidate.final_score, future_value, max(0.0, candidate.final_score + future_value - total), total, horizon)
        return sorted(candidates, key=lambda item: scores[id(item)].total, reverse=True), scores

