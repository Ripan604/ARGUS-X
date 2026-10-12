"""Render the retained exploratory packet-imaging results without rerunning them."""
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "research_results/wave_packet_imaging_development_2026_10_12.json"
QUALIFIED = ROOT / "research_results/qualified_wave_packet_imaging_development_2026_10_12.json"
DOC = ROOT / "docs/WAVE_PACKET_DEVELOPMENT_RESULTS_2026_10_12.md"
FIGURE = ROOT / "output/figures/wave_packet_development_2026_10_12.png"
MAPS = ROOT / "output/figures/wave_packet_maps_2026_10_12.png"


def read_result(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Bounded retained result required")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not result["completed"] or result["metadata"]["source_changed_during_run"]:
        raise ValueError("Incomplete or source-changing experiment cannot become a report")
    return result


def main():
    if any(path.exists() for path in (DOC, FIGURE, MAPS)):
        raise SystemExit("Dated report exists; preserve it instead of overwriting")
    first, qualified = read_result(FIRST), read_result(QUALIFIED)
    for row in qualified["runs"]:
        sets = [set(row["used_path_indices"]), set(row["qualification_rejected_path_indices"]),
                {failure["path_index"] for failure in row["processing_failures"]}]
        if (sum(len(s) for s in sets) != row["budget"]
                or set.union(*sets) != set(row["queried_path_indices"])):
            raise ValueError("Common opportunity accounting is inconsistent")
    select = lambda method: next(row for row in qualified["summary"]
        if row["context"] == "condition_matched_baseline" and row["budget"] == 66 and row["method"] == method)
    directional = select("qualified_directional_packet")
    isotropic = select("qualified_isotropic_packet")
    positions = ("D04", "D12", "D16", "D24")
    cases = [next(row for row in qualified["runs"] if row["context"] == "condition_matched_baseline"
        and row["budget"] == 66 and row["method"] == "qualified_directional_packet"
        and row["nominal_temperature_c"] == 40 and row["test_state"] == state) for state in positions]
    reference = next(row for row in qualified["qualifications"]
        if row["method"] == "qualified_directional_packet" and row["reference_temperature_c"] == 40)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), layout="constrained")
    labels = ["Directional / 40 C\n4 of 12 conditions", "Isotropic / 60 C\n4 of 12 conditions"]
    x = np.arange(2)
    for offset, key, label, color in [(-.24, "paired_raw_RAPID_mean_error_mm", "RAPID", "#8594a4"),
            (0, "paired_first_study_all_path_mean_error_mm", "All-path packets", "#dd9959"),
            (.24, "paired_qualified_mean_error_mm", "Qualified packets", "#188f93")]:
        values = [directional[key], isotropic[key]]
        bars = axes[0].bar(x + offset, values, .23, label=label, color=color)
        axes[0].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[0].set(xticks=x, xticklabels=labels, ylabel="Paired mean location error (mm)",
                title="Same physical cases, same 66 opportunities", ylim=(0, 370))
    axes[0].legend(fontsize=8)
    p = np.arange(4)
    axes[1].bar(p - .17, [row["paired_raw_RAPID_error_mm"] for row in cases], .34, label="RAPID", color="#8594a4")
    bars = axes[1].bar(p + .17, [row["location_error_mm"] for row in cases], .34, label="Qualified", color="#188f93")
    axes[1].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[1].set(xticks=p, xticklabels=positions, ylabel="Location error (mm)", title="Directional 40 C: all four cases")
    axes[1].legend(fontsize=8)
    axes[2].semilogy(range(66), reference["energy_ratios"], color="#188f93", marker=".", linewidth=1)
    axes[2].axhline(.1, color="#b0444f", linestyle="--", label="Declared lower norm ratio")
    ratio = reference["energy_ratios"][60]
    axes[2].annotate(f"Path 60: {ratio:.4f}\nT9 to T10", xy=(60, ratio), xytext=(30, .012),
                     arrowprops={"arrowstyle": "->", "color": "#b0444f"}, fontsize=9)
    axes[2].set(xlabel="Recorded path index", ylabel="Healthy receiver/source norm / anchor median",
                title="Healthy-reference consistency, 40 C", ylim=(.001, 15))
    axes[2].legend(fontsize=8)
    fig.suptitle("Exploratory development on one previously inspected CFRP plate", fontsize=14)
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)
    map_case = cases[1]
    all_path = next(row for row in first["runs"] if row["context"] == "condition_matched_baseline"
        and row["budget"] == 66 and row["method"] == "directional_packet"
        and row["nominal_temperature_c"] == 40 and row["test_state"] == "D12")
    rapid = next(row for row in qualified["runs"] if row["context"] == "condition_matched_baseline"
        and row["budget"] == 66 and row["method"] == "raw_RAPID"
        and row["nominal_temperature_c"] == 40 and row["test_state"] == "D12")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), layout="constrained")
    for ax, row, label in zip(axes, (rapid, all_path, map_case), ("RAPID", "All-path packets", "Qualified packets")):
        values = np.array(row["raw_intensity"]).reshape(50, 50)
        relative = values / values.max() if values.max() > 0 else values
        im = ax.imshow(relative, origin="lower", extent=(0, 500, 0, 500), vmin=0, vmax=1, cmap="magma")
        truth, peak = np.array(row["reference_truth_m"]) * 1000, np.array(row["map_m"]) * 1000
        ax.scatter(*truth, s=90, facecolors="none", edgecolors="#61e2dc", label="Reference mass")
        ax.scatter(*peak, marker="x", s=60, color="white", label="Image peak")
        ax.set(title=f"{label}\nerror {row['location_error_mm']:.1f} mm", xlabel="X (mm)", ylabel="Y (mm)")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.colorbar(im, ax=axes, shrink=.85, label="Intensity / each image's own peak; not probability")
    fig.suptitle("D12, 40 C, 66 opportunities — illustrative previously seen case", fontsize=13)
    fig.savefig(MAPS, dpi=150)
    plt.close(fig)
    rows = "\n".join(f"| {state} | {case['paired_raw_RAPID_error_mm']:.2f} | {case['location_error_mm']:.2f} |"
                       for state, case in zip(positions, cases))
    document = f"""# Wave-packet development results — 12 October 2026

This development iteration improves the operator UI, adds time-resolved
experimental imaging, and identifies a concrete reference-validity issue.
It does not establish field detection, a new patentable method or a successful
complete-temperature localization model. Both experiments use previously
inspected OGW measurements from one plate and four collinear removable mass
positions. No new physical acquisition was performed.

## Measured comparisons and coverage

Healthy-only propagation calibration qualified two of six models. Four fits
reached the declared instrument-delay bound; their results remain unsupported.
The first experiment used all recorded paths and worsened localization.
The second uses paths that agree with the healthy delay fit and pass a
source-normalized healthy-reference norm check. These are exploratory revisions,
not untouched confirmation.

All errors below compare exactly the same eligible four position/temperature
cases. Each method consumes 66 common recorded opportunities, including rejected
ones. The directional branch contributes 45 paths, and the isotropic branch 36.

| Branch | Usable damage conditions | RAPID (mm) | All-path packet (mm) | Qualified packet (mm) |
|---|---:|---:|---:|---:|
| Directional, 40 C | 4 / 12 | {directional['paired_raw_RAPID_mean_error_mm']:.2f} | {directional['paired_first_study_all_path_mean_error_mm']:.2f} | {directional['paired_qualified_mean_error_mm']:.2f} |
| Isotropic, 60 C | 4 / 12 | {isotropic['paired_raw_RAPID_mean_error_mm']:.2f} | {isotropic['paired_first_study_all_path_mean_error_mm']:.2f} | {isotropic['paired_qualified_mean_error_mm']:.2f} |

Directional 40 C improves all four paired cases, but the D16 error remains
143.96 mm. Isotropic 60 C still performs worse than RAPID on average. Each
packet branch supports only one of three healthy comparison conditions.
Both fixed-20 packet branches remain unsupported. Missing conditions are not
excluded silently or assigned zero error.

| Directional 40 C position | RAPID error (mm) | Qualified error (mm) |
|---|---:|---:|
{rows}

![Paired errors and healthy reference consistency](../output/figures/{FIGURE.name})

## What the quality gate establishes

Healthy 40 C path 60 (T9 to T10) has receiver L2 norm 0.03274 after filtering,
versus 10.21266 at 20 C and 9.85255 at 60 C. Its source-normalized norm ratio
to the three-anchor median is {ratio:.6f}. This is an amplitude/transfer
consistency proxy, not a squared physical-energy ratio or a damage probability.
A receiver dropout is a possible explanation, not a verified cause.

The implementation rejects abnormal reference ratios and paths outside the
healthy delay model's inliers. Path 60 was already excluded by the inlier rule,
so these data do not establish an independent benefit of the norm gate.
The observed improvement belongs to the combined path-qualification branch.
The raw healthy image remains descriptive; no damage threshold, sensitivity
or false-positive rate is calibrated. Test electrical source drift is not yet
corrected in this branch.

![D12 raw intensity comparisons](../output/figures/{MAPS.name})

Each displayed image uses its own peak as the colour maximum. This supports
pattern inspection only; colours cannot compare absolute evidence strength
between methods. Raw intensities remain in the result files.

## Implementation and evidence

- `backend/app/evaluation/wave_packet_imaging.py`: source-correlation residual
  envelopes, bounded healthy packet-delay fits and time-resolved backprojection.
- `backend/app/evaluation/wave_packet_qualification.py`: healthy transfer-norm
  consistency and model-inlier gating, separate from damage decisions.
- [First protocol](WAVE_PACKET_IMAGING_PROTOCOL.md) and
  [qualified-path protocol](QUALIFIED_WAVE_PACKET_PROTOCOL.md).
- [First retained result](../research_results/{FIRST.name}), SHA-256
  `{sha256(FIRST.read_bytes()).hexdigest()}`.
- [Qualified retained result](../research_results/{QUALIFIED.name}), SHA-256
  `{sha256(QUALIFIED.read_bytes()).hexdigest()}`.

Both runs completed 270 comparison rows with unchanged source hashes.
The qualified run reproduced the first run's RAPID control exactly. Its path
sets account for every common opportunity as used, rejected or failed.
Counts reuse 18 physical banks; they are not 540 independent physical trials.

Exact sources were preserved under `output/research_sources/` in separate
`wave_packet_imaging_2026_10_12_v1` and
`qualified_wave_packet_imaging_2026_10_12_v1` snapshots, with verified SHA-256
manifests. Subsequent hardening rejects minimum-signed-integer amplitude
overflow and negative/duplicate/out-of-range calibration indices. Those fixes
do not change valid native-bank numerics; the frozen experiment sources remain
available and the experiments were not replaced after inspecting the results.

Delay-and-sum, Hilbert envelopes and directional propagation calibration are
established methods; the protocols cite primary literature. This experiment
does not establish novelty. The new branch remains offline and does not alter
production structural decisions.

## Next development step

Correct measured source timing/gain using only each captured electrical source,
then improve healthy packet identification and model identifiability without
using damaged receiver responses. Freeze the revised policy before genuinely
uninspected tests. Independent panels and a blind apparatus campaign are needed
to assess practical localization and detection; software checks cannot supply
that physical evidence.
"""
    DOC.write_text(document, encoding="utf-8")
    print(json.dumps({"report": str(DOC.relative_to(ROOT)), "figures": [str(FIGURE.relative_to(ROOT)), str(MAPS.relative_to(ROOT))],
                      "qualified_result_sha256": sha256(QUALIFIED.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
