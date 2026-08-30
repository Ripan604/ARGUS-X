# Reproducibility

## Environment and one-command run

ARGUS targets Python 3.11+ and Node 22+, uses local SQLite, requires no Docker/GPU/paid API, and keeps all generated research artifacts local.

```powershell
python -m pip install -r backend\requirements.txt
cd frontend; npm install; cd ..
python scripts\doctor.py
.\run_argus.ps1
```

The launcher initializes the database through additive migrations, starts backend/frontend, and prints local, phone, and edge URLs. `Ctrl+C` terminates both children.

## Quality gate

```powershell
python -m pytest backend\tests -q
cd frontend
npm test
npm run lint
npm run build
cd ..
python scripts\neo_calibration.py --quick
python scripts\neo_benchmark.py --cases 2 --max-experiments 5
python scripts\run_neo_demo.py rival_hypotheses --output research_results\rival.json
python scripts\run_neo_demo.py model_mismatch --output research_results\mismatch.json
```

Seeds, configuration, action score components, signals, posterior transitions, software revision, and hashes are persisted. Counterfactual truth is inaccessible until `end_blind_evaluation()`. Synthetic banks support `tiny`, `demo`, and `research` scales with chunk manifests and resume.

Calibration modes contain 4/16/64 trials:

```powershell
python scripts\neo_calibration.py --quick
python scripts\neo_calibration.py --standard
python scripts\neo_calibration.py --research
```

The command writes JSON, coverage CSV, reliability SVG, and rank-histogram SVG. Quick modes prove execution, not statistical adequacy. For a paper, archive the full configuration, environment versions, commit, raw result JSON, excluded/failed runs, and bundle head hashes.

