from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
import secrets
from threading import RLock

from backend.app.database.repository import SessionRepository


ROOT = Path(__file__).resolve().parents[3]
MAX_SEED = 2_147_483_647
MAX_ACTIVE_JOBS = 8
logger = logging.getLogger("argus.research")


class ResearchJobManager:
    def __init__(self, repository: SessionRepository, workers: int = 1) -> None:
        self.repository = repository
        self.repository.recover_interrupted_jobs()
        self.executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="argus-research")
        self._lock = RLock()

    def submit(self, job_type: str, request: dict) -> dict:
        if job_type not in {"benchmark", "calibration", "ablation", "dataset_generation", "surrogate_training", "demo_scenario"}:
            raise ValueError(f"Unsupported research job type: {job_type}")
        request = self._validated_request(job_type, request)
        with self._lock:
            if self.repository.count_active_jobs() >= MAX_ACTIVE_JOBS:
                raise ValueError(f"At most {MAX_ACTIVE_JOBS} research jobs may be queued or running")
            job_id = secrets.token_urlsafe(12)
            self.repository.create_job(job_id, job_type, request)
            self.executor.submit(self._run, job_id, job_type, request)
        return self.repository.get_job(job_id)

    @staticmethod
    def _integer(request: dict, name: str, default: int, minimum: int, maximum: int) -> int:
        raw = request.get(name, default)
        if isinstance(raw, bool):
            raise ValueError(f"{name} must be an integer")
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if isinstance(raw, float) and not raw.is_integer():
            raise ValueError(f"{name} must be an integer")
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return value

    @classmethod
    def _validated_request(cls, job_type: str, request: dict) -> dict:
        if not isinstance(request, dict):
            raise ValueError("Research-job parameters must be an object")
        allowed = {
            "benchmark": {"cases", "max_experiments", "seed"},
            "ablation": {"cases", "seed"},
            "calibration": {"mode", "seed"},
            "dataset_generation": {"destination", "scale", "seed", "resume"},
            "surrogate_training": {"samples", "query_count", "seed"},
            "demo_scenario": {"scenario", "cases", "seed"},
        }[job_type]
        unexpected = sorted(set(request) - allowed)
        if unexpected:
            raise ValueError(f"Unsupported parameters for {job_type}: {', '.join(unexpected)}")

        seed_defaults = {
            "benchmark": 100,
            "ablation": 300,
            "calibration": 200,
            "dataset_generation": 71,
            "surrogate_training": 431,
            "demo_scenario": 17,
        }
        seed = cls._integer(request, "seed", seed_defaults[job_type], 0, MAX_SEED)
        if job_type == "benchmark":
            return {
                "cases": cls._integer(request, "cases", 2, 1, 25),
                "max_experiments": cls._integer(request, "max_experiments", 5, 2, 30),
                "seed": seed,
            }
        if job_type == "ablation":
            return {"cases": cls._integer(request, "cases", 2, 1, 25), "seed": seed}
        if job_type == "calibration":
            mode = str(request.get("mode", "quick"))
            if mode not in {"quick", "standard", "research"}:
                raise ValueError("mode must be quick, standard, or research")
            return {"mode": mode, "seed": seed}
        if job_type == "surrogate_training":
            samples = cls._integer(request, "samples", 240, 180, 5_000)
            query_count = cls._integer(request, "query_count", 24, 1, samples)
            return {"samples": samples, "query_count": query_count, "seed": seed}
        if job_type == "demo_scenario":
            scenario = str(request.get("scenario", "rival_hypotheses"))
            if scenario not in {"rival_hypotheses", "model_mismatch", "measurement_compression"}:
                raise ValueError("Unknown demo scenario")
            return {
                "scenario": scenario,
                "cases": cls._integer(request, "cases", 4, 1, 25),
                "seed": seed,
            }

        scale = str(request.get("scale", "tiny"))
        if scale not in {"tiny", "demo", "research"}:
            raise ValueError("scale must be tiny, demo, or research")
        resume = request.get("resume", True)
        if not isinstance(resume, bool):
            raise ValueError("resume must be a boolean")
        generated_root = (ROOT / "datasets" / "generated").resolve()
        raw_destination = Path(str(request.get("destination", "datasets/generated/counterfactual_bank")))
        destination = (raw_destination if raw_destination.is_absolute() else ROOT / raw_destination).resolve()
        if not destination.is_relative_to(generated_root) or destination == generated_root:
            raise ValueError("destination must be a subdirectory of datasets/generated")
        return {"destination": str(destination), "scale": scale, "seed": seed, "resume": resume}

    def cancel(self, job_id: str) -> dict:
        job = self.repository.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        self.repository.update_job(job_id, cancellation_requested=True)
        return self.repository.get_job(job_id)

    def _cancelled(self, job_id: str) -> bool:
        job = self.repository.get_job(job_id)
        return bool(job and job["cancellation_requested"])

    def _run(self, job_id: str, job_type: str, request: dict) -> None:
        if self._cancelled(job_id):
            self.repository.update_job(job_id, status="cancelled", progress=1.0)
            return
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
            logger.exception("research_job_failed id=%s type=%s", job_id, job_type)
            self.repository.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
