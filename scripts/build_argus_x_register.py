"""Build a traceable disposition register from the ARGUS-X master inventory.

The generated register does not convert acknowledged risks into completed work.
It deliberately separates software controls from research and physical-validation
obligations so progress can be audited without inflated claims.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import shutil


ITEM = re.compile(r"^([A-Z]{1,2}\d+)\.\s*(.*)$")
SECTION = re.compile(r"^([A-Z]{1,2})\.\s+(.+)$")

EXTERNAL_SECTIONS = {"B", "C", "G", "U", "W", "AJ", "AU", "AY", "AZ", "BI"}
LITERATURE_SECTIONS = {"AR", "BJ", "BL"}
PARTIAL_SECTIONS = {
    "A", "D", "F", "H", "I", "M", "N", "O", "P", "Q", "R", "S", "T", "X", "Y", "Z",
    "AA", "AF", "AG", "AH", "AI", "AK", "AL", "AM", "AN", "AO", "AP", "AQ", "AS", "AT", "AV",
    "AW", "AX", "BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BM", "BO", "BQ",
}

# These are narrow, executable controls with direct test evidence. The status does
# not imply certification or validation outside the stated software boundary.
IMPLEMENTED_TESTED = {
    "A2", "A3", "A24", "A26", "A29", "A30", "A32",
    "C24", "C25", "C26", "C27", "C28",
    "M10", "M14", "M19",
    "N10", "N18", "N19", "O7", "O8", "O9", "O10", "O11", "O12", "O13",
    "P12", "P13", "P14", "P15", "P23", "P25", "P26", "P32", "P41", "P42", "P44", "P45", "P46", "P47", "P48", "P49",
    "Q3", "Q4", "Q7", "Q11", "Q12", "Q13",
    "R9", "R11", "R12", "R13", "R14",
    "X7", "X8", "X9", "X11", "X12", "X13", "X14", "X16", "X17", "X18",
    "Y11", "Y15", "Y16", "Y19", "Y20", "Z11", "Z12", "Z15", "Z18", "Z19", "Z20", "Z22",
    "AA1", "AA11", "AA12", "AA13", "AA15", "AA16", "AA17", "AA18", "AA19", "AA20",
    "AF1", "AF5", "AF7", "AF8", "AF9", "AF10", "AF20",
    "AG10", "AH5", "AH6", "AH7", "AH8", "AH9", "AH10", "AH11", "AH12",
    "AI1", "AI2", "AI3", "AI4", "AI5", "AI6", "AI7", "AI8", "AI9", "AI10", "AI11", "AI12", "AI13", "AI14", "AI15", "AI16", "AI17", "AI18", "AI19", "AI20", "AI21", "AI22",
    "AJ4", "AJ5", "AJ6", "AJ7", "AJ16", "AJ17", "AJ18",
    "AK3", "AK4", "AK13", "AK15",
    "AL2", "AL3", "AL4", "AL5", "AL6", "AL7", "AL9", "AL10", "AL11", "AL12", "AL13", "AL14", "AL17", "AL18", "AL19",
    "AM4", "AM5", "AM6", "AM7", "AM8", "AM9", "AM10", "AM11", "AM12", "AM15",
    "AS3", "AS4", "AS8", "AS10", "AS11", "AS12", "AS13",
    "AT3", "AT4", "AT8", "AT9", "AT10", "AT11", "AT12",
    "AW1", "AW2", "AW3", "AW4", "AW5", "AW6", "AW7", "AW8", "AW9", "AW10", "AW11",
    "AX1", "AX2", "AX3", "AX5", "AX6", "AX8", "AX9", "AX10", "AX12", "AX13", "AX14",
    "BA1", "BA2", "BA3", "BA4", "BA5", "BA6",
    "BC8", "BC9", "BC10", "BC11", "BC12", "BC13", "BC14", "BC15",
    "BD1", "BD2", "BD4", "BD5", "BD6", "BD7", "BD8", "BD9", "BD11", "BD12",
    "BE1", "BE2", "BE3", "BE4", "BE5", "BE6", "BE7", "BE13",
    "BF1", "BF3", "BF4", "BF5", "BF6", "BF8", "BF9", "BF10", "BF11", "BF12",
    "BG3", "BG5", "BG6", "BG7", "BG8", "BG9", "BG10", "BG11", "BG12",
    "BM1", "BM2", "BM3", "BM4", "BM5", "BM6", "BM7", "BM8", "BM9", "BM10",
    "BQ1", "BQ2", "BQ7", "BQ8", "BQ9", "BQ10", "BQ11", "BQ15", "BQ16", "BQ17", "BQ18", "BQ20", "BQ21", "BQ22", "BQ23", "BQ24", "BQ25", "BQ26", "BQ27", "BQ30", "BQ32", "BQ33",
}

EVIDENCE_BY_SECTION = {
    "A": "backend/app/assurance/monitor.py; backend/app/decision/loss.py",
    "B": "backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md",
    "C": "backend/app/inference/diagnostics.py; backend/app/services/session_manager.py",
    "D": "backend/app/signal/processing.py",
    "F": "scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md",
    "G": "backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md",
    "M": "backend/app/inference; backend/tests/test_inference.py",
    "N": "backend/app/inference/calibration.py; scripts/neo_calibration.py",
    "O": "backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md",
    "P": "backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py",
    "Q": "backend/app/decision/loss.py",
    "R": "backend/app/decision/stopping.py",
    "S": "backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py",
    "T": "backend/app/inference/structural_posterior.py",
    "X": "backend/app/assurance/monitor.py; backend/app/research/faults.py",
    "Y": "backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py",
    "Z": "backend/app/digital_twin; backend/app/inference/nuisance_posterior.py",
    "AA": "docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results",
    "AG": "backend/app/evidence/ledger.py; backend/app/services/session_manager.py",
    "AH": "backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx",
    "AI": "backend/app/evidence/ledger.py; backend/app/database/repository.py",
    "AJ": "backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx",
    "AK": "backend/app/main.py; scripts/doctor.py",
    "AL": "backend/tests; frontend/tests; backend/app/replay",
    "AM": "backend/app/database; backend/app/evidence/bundles.py",
    "AN": "backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py",
    "AO": "docs/BENCHMARK_PROTOCOL.md; backend/app/replay",
    "AP": "backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py",
    "AQ": "scripts/neo_benchmark.py; research_results/neo_ablation_quick.json",
    "AR": "docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md",
    "AS": "backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx",
    "AT": "backend/app/safety/constraints.py; emergency-stop API",
    "AW": "frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx",
    "AX": "docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay",
    "BA": "backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py",
    "BC": "backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py",
    "BD": "backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py",
    "BE": "backend/app/decision/loss.py; backend/app/active_learning/planner.py",
    "BF": "backend/app/services/session_manager.py; backend/app/inference/diagnostics.py",
    "BG": "frontend/components; frontend/app/page.tsx",
    "BH": "backend/app/assurance/monitor.py; backend/app/models/registry.py",
    "BJ": "paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md",
    "BL": "docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md",
    "BM": "backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md",
    "BO": "docs/ARGUS_X_DISPOSITION.md",
    "BQ": "docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components",
}


def parse_inventory(text: str) -> list[dict[str, str | int]]:
    section_code, section_title = "", ""
    items: list[dict[str, str | int]] = []
    current: dict[str, str | int] | None = None
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        section_match = SECTION.match(line)
        if section_match and not ITEM.match(line):
            section_code, section_title = section_match.groups()
            continue
        item_match = ITEM.match(line)
        if item_match:
            if current:
                current["problem"] = " ".join(str(current["problem"]).split())
                items.append(current)
            code, problem = item_match.groups()
            current = {
                "id": code,
                "section": re.match(r"[A-Z]+", code).group(0),
                "section_title": section_title,
                "source_line": line_number,
                "problem": problem,
            }
        elif current and line and not line.startswith("=") and not line.startswith("Recent "):
            current["problem"] = f"{current['problem']} {line}"
    if current:
        current["problem"] = " ".join(str(current["problem"]).split())
        items.append(current)
    return items


def classify(item: dict[str, str | int]) -> tuple[str, str]:
    code, section = str(item["id"]), str(item["section"])
    if code in IMPLEMENTED_TESTED:
        return "implemented_and_tested", "Executable software control; scope remains research-only."
    if section in EXTERNAL_SECTIONS:
        return "requires_physical_validation", "Cannot be closed honestly without representative hardware/panels and independent ground truth."
    if section in LITERATURE_SECTIONS:
        return "requires_literature_or_legal_review", "Evidence is documented, but publication/patent conclusions require a current professional search or review."
    if section in PARTIAL_SECTIONS:
        return "partially_mitigated", "A bounded software mechanism or test exists; broader robustness/generalization remains open."
    return "acknowledged_and_bounded", "Recorded in the risk register and bounded as an explicit limitation or future experiment."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ARGUS-X master inventory text file")
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8", errors="replace")
    items = parse_inventory(text)
    if len(items) < 500:
        raise SystemExit(f"Inventory parse produced only {len(items)} items; refusing incomplete register")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = args.output_dir / "ARGUS_X_MASTER_INVENTORY.txt"
    shutil.copyfile(args.source, snapshot)

    rows = []
    for item in items:
        status, disposition = classify(item)
        rows.append({
            **item,
            "status": status,
            "disposition": disposition,
            "evidence": EVIDENCE_BY_SECTION.get(str(item["section"]), "docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md"),
        })

    csv_path = args.output_dir / "ARGUS_X_PROBLEM_REGISTER.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    md = [
        "# ARGUS-X problem disposition register",
        "",
        f"Generated from the complete master inventory. **{len(rows)} uniquely identified problems are accounted for.**",
        "",
        "> A status of `implemented_and_tested` means a narrow executable software control exists. It does not imply physical validation, certification, safety approval, or patentability.",
        "",
        "## Status summary",
        "",
        "| Status | Count |",
        "|---|---:|",
        *[f"| `{key}` | {value} |" for key, value in sorted(counts.items())],
        "",
        "## Complete register",
        "",
        "| ID | Section | Problem | Status | Evidence / boundary |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        problem = str(row["problem"]).replace("|", "\\|")
        evidence = str(row["evidence"]).replace("|", "\\|")
        md.append(f"| {row['id']} | {row['section_title']} | {problem} | `{row['status']}` | {evidence} |")
    (args.output_dir / "ARGUS_X_PROBLEM_REGISTER.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (args.output_dir / "ARGUS_X_PROBLEM_REGISTER.summary.json").write_text(
        json.dumps({"source": snapshot.name, "problem_count": len(rows), "status_counts": counts}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"problem_count": len(rows), "status_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
