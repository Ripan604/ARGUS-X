from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import secrets
from threading import RLock

from backend.app.database.repository import SessionRepository


class ResearchJobManager:
    def __init__(self, repository: SessionRepository, workers: int = 1) -> None:
        self.repository = repository
        self.repository.recover_interrupted_jobs()
        self.executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="argus-research")
        self._lock = RLock()

    def submit(self, job_type: str, request: dict) -> dict:
        if job_type not in {"benchmark", "calibration", "ablation", "dataset_generation", "surrogate_training", "demo_scenario"}:
            raise ValueError(f"Unsupported research job type: {job_type}")
        job_id = secrets.token_urlsafe(12)
        self.repository.create_job(job_id, job_type, request)
        self.executor.submit(self._run, job_id, job_type, request)
        return self.repository.get_job(job_id)

    def cancel(self, job_id: str) -> dict:
        if self.repository.get_job(job_id) is None:
            raise KeyError(job_id)
        self.repository.update_job(job_id, cancellation_requested=True)
        return self.repository.get_job(job_id)

    def _cancelled(self, job_id: str) -> bool:
        job = self.repository.get_job(job_id)
        return bool(job and job["cancellation_requested"])

    def _run(self, job_id: str, job_type: str, request: dict) -> None:
        self.repository.update_job(job_id, status="running", progress=0.01)

        def progress(value: float) -> None:
            self.repository.update_job(job_id, progress=max(0.0, min(1.0, float(value))))

        try:
            if job_type == "demo_scenario":
                from backend.app.demo.scenarios import run_demo_scenario

                result = run_demo_scenario(
                    request.get("scenario", "rival_hypotheses"), seed=request.get("seed"),
                    cases=int(request.get("cases", 4)), progress=progress,
                    cancelled=lambda: self._cancelled(job_id),
                )
            elif job_type == "surrogate_training":
                from backend.app.models.active_learning import run_active_learning_study

                result = run_active_learning_study(
                    seed=int(request.get("seed", 431)), samples=int(request.get("samples", 240)),
                    query_count=int(request.get("query_count", 24)), progress=progress,
                    cancelled=lambda: self._cancelled(job_id),
                )
                if not result.get("cancelled"):
                    from backend.app.models.registry import ModelRegistry

                    ModelRegistry(self.repository).register(
                        f"active-mlp-{job_id}", "MLP ensemble (3 x 48,48)",
                        training_dataset_hash=result["training_dataset_hash"],
                        metrics={
                            "initial_test_mae": result["initial_test_mae"],
                            "active_test_mae": result["active_test_mae"],
                            "relative_mae_change": result["relative_mae_change"],
                        },
                        supported_domain={"source": "physics_simulation", "input_schema": "ARGUS forward v1"},
                    )
            elif job_type == "dataset_generation":
                from backend.app.research.bank import generate_counterfactual_bank

                result = generate_counterfactual_bank(
                    request.get("destination", "datasets/generated/counterfactual_bank"),
                    scale=request.get("scale", "tiny"), seed=int(request.get("seed", 71)),
                    resume=bool(request.get("resume", True)), progress=progress,
                    cancelled=lambda: self._cancelled(job_id),
                )
            elif job_type == "calibration":
                from backend.app.evaluation.calibration_study import run_calibration_study

                result = run_calibration_study(
                    mode=request.get("mode", "quick"), seed=int(request.get("seed", 200)),
                    progress=progress, cancelled=lambda: self._cancelled(job_id),
                )
            elif job_type == "ablation":
                from backend.app.evaluation.neo_benchmark import run_ablation_study

                result = run_ablation_study(
                    cases=int(request.get("cases", 2)), seed=int(request.get("seed", 300)), progress=progress,
                    cancelled=lambda: self._cancelled(job_id),
                )
            else:
                from backend.app.evaluation.neo_benchmark import run_benchmark_matrix

                result = run_benchmark_matrix(
                    cases=int(request.get("cases", 2)), max_experiments=int(request.get("max_experiments", 5)),
                    seed=int(request.get("seed", 100)), progress=progress,
                    cancelled=lambda: self._cancelled(job_id),
                )
            if self._cancelled(job_id):
                self.repository.update_job(job_id, status="cancelled", progress=1.0, result=result)
            else:
                self.repository.update_job(job_id, status="completed", progress=1.0, result=result)
        except Exception as exc:
            self.repository.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
