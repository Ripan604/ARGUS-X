"""Build a small source-checked summary of the frozen v2 evidence, locally."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "research_results/extended_reference_design_2026_10_07.json"
report = json.loads(STUDY.read_text(encoding="utf-8"))
metadata = report["metadata"]
if metadata["source_changed_during_run"] or metadata["source_sha256_before"] != metadata["source_sha256_after"]:
    raise RuntimeError("Extended study did not run against a frozen source")
for name, digest in metadata["source_sha256_after"].items():
    if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Extended-study source changed: {name}")
frontend = json.loads((ROOT / "output/release/frontend-checks.json").read_text())
if not frontend["all_passed"] or frontend["source_changed_during_run"]:
    raise RuntimeError("Frontend checks did not pass against frozen source")
for name, digest in frontend["source_sha256"].items():
    if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Frontend source changed: {name}")
suite = ET.parse(ROOT / "output/release/probe-v2-backend-tests.xml").getroot().find("testsuite")
if suite is None or int(suite.attrib["failures"]) or int(suite.attrib["errors"]):
    raise RuntimeError("Backend full suite did not pass")
tests, skipped = int(suite.attrib["tests"]), int(suite.attrib["skipped"])
paired = [{k: v for k, v in p.items() if k != "seed_cluster_differences"}
          for p in report["paired"]]
failure_counts = Counter(step["error"] for run in report["runs"] for step in run["trace"] if not step["accepted"])
summary = {
    "revision": "probe-v2", "evidence_scope": "synthetic_scalar_reference_not_physical_localization",
    "backend": {"passed": tests-skipped, "skipped": skipped, "failures": 0,
                "junit_sha256": sha256((ROOT / "output/release/probe-v2-backend-tests.xml").read_bytes()).hexdigest()},
    "frontend": frontend["checks"],
    "study": {"file": STUDY.relative_to(ROOT).as_posix(), "sha256": sha256(STUDY.read_bytes()).hexdigest(),
              "attempted_runs": len(report["runs"]), "completed_runs": sum(r["completed"] for r in report["runs"]),
              "failed_opportunities": sum(r["failures"] for r in report["runs"]),
              "seed_clusters": len(metadata["seed_list"]), "source_hashes_current": True,
              "failure_reasons": dict(failure_counts), "summary": report["summary"], "paired": paired},
    "physical_measurements_performed": False,
    "publication_or_grant_probability_established": False,
}
(ROOT / "output/probe_v2_evidence_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
lines = ["\n## Dated verification and extended comparison\n",
    f"The full backend suite passed {tests-skipped} tests, with {skipped} intentionally skipped legacy-pickle checkpoint test. "
    "A nonfatal framework deprecation warning remains. All 30 frontend tests, TypeScript checking, lint and production build passed.\n",
    "The extended study used 48 independent seed clusters, four fixed diagnostic geometries, two prespecified noise regimes, "
    "five reference policies and three opportunities each. Sealed truth/noise were never supplied to selection. "
    "The A/D baselines use dimensionless covariance scales and the same declared cost conversion; cyclic/random are charged the same costs.\n",
    f"All {len(report['runs']):,} attempted runs remain in the means and paired contrasts. "
    f"{summary['study']['completed_runs']:,} completed without a rejected opportunity; {summary['study']['failed_opportunities']} "
    "reference-update opportunities were rejected. The failed runs consume their budget and retain the current state. "
    "Source hashes were unchanged during the run and match the current backend.\n",
    "| Regime / reference policy | Arrival RMSE (microseconds) | Latent 95% interval coverage | Completed / attempted |",
    "|---|---|---|---|"]
for regime, policies in report["summary"].items():
    for policy, row in policies.items():
        lines.append(f"| {regime.replace('_',' ')} / {policy.replace('_',' ')} | {row['mean_target_arrival_rmse_us']:.2f} | "
                     f"{100*row['mean_posterior_weighted_95_interval_coverage']:.2f}% | {row['completed_runs']} / {row['attempted_runs']} |")
lines += ["\nPooled paired advantages are comparator minus task RMSE: positive favours task selection. "
          "Intervals resample the 48 seed clusters, preserving within-seed geometry/regime dependence. "
          "They are exploratory 95% intervals without multiplicity correction.\n",
          "| Comparator | Mean task advantage (microseconds) | Seed-cluster 95% interval | Interpretation |",
          "|---|---|---|---|"]
for p in paired:
    if p["regime_group"] == "all_regimes" and p["metric"] == "target_arrival_rmse_us":
        lo, hi = p["seed_cluster_bootstrap_95ci"]
        interpretation = "Interval above zero in this model" if lo > 0 else "Inconclusive difference"
        lines.append(f"| {p['baseline'].replace('_',' ')} | {p['mean_advantage_for_task_conditioned']:.2f} | [{lo:.2f}, {hi:.2f}] | {interpretation} |")
lines += ["\nThe D-optimal comparison is inconclusive for both pooled arrival RMSE and prediction-plus-cost. "
    "Task RMSE is slightly worse than D-optimal under doubled noise. No general superiority claim is supported. "
    "Under nominal noise, task selection improves arrival prediction while worsening timing-offset parameter error "
    "(186.23 versus 168.23 microseconds for cyclic). These different outcomes must not be conflated.\n",
    "Task latent-arrival interval coverage is 91.83% under nominal noise and 66.19% under doubled noise. "
    "These first-order parameter intervals do not achieve nominal 95% coverage in the study and do not certify physical defect confidence. "
    "The rejection reason retained by the study is: " + "; ".join(f"{k} ({v} opportunities)" for k,v in failure_counts.items()) + ".\n",
    "The earlier 192-run scalar study and 48-run waveform localization study remain historical, source-bound evidence. "
    "This larger scalar study does not replace the need for measured waveforms, independent defect truth or a blind physical campaign.\n",
    "## What remains before stronger publication and patent claims\n",
    "The code and disclosure can now undergo a substantive technical review. A measured timing/transfer bench and blind specimen-held-out "
    "adaptive inspection are still missing. The apparatus compilation status is stated in PROBE_V2_DESIGN.md. "
    "Real inventors, ownership, conception records and earlier public disclosures need confirmation. "
    "Claim-specific novelty and inventive-step analysis remains open against close active-calibration and acoustic-reference prior art.\n",
    "No justified 10/10 publication readiness or 6/10 grant probability follows from the implemented changes. "
    "Patent application publication is a filing procedure, whereas substantive grant depends on examination. "
    "A manuscript publication also depends on the venue and its reviewers. The package is locally prepared; it has not been filed or published.\n"]
doc = ROOT / "docs/PROBE_V2_RELEASE_REVIEW.md"
content = doc.read_text(encoding="utf-8").split("\n## Dated verification and extended comparison")[0]
doc.write_text(content.rstrip()+"\n"+"\n".join(lines)+"\n", encoding="utf-8")
print(json.dumps({"backend_passed": tests-skipped, "frontend_tests": 30,
                  "runs": len(report['runs']), "completed": summary['study']['completed_runs'],
                  "failed_opportunities": summary['study']['failed_opportunities'], "source_hashes_current": True}))
