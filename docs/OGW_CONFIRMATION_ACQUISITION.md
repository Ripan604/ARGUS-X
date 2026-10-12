# Separate OGW calibration and confirmation acquisition

**Selection fixed 8 October 2026, before any new waveform analysis.** The source
is the CC0 [OGW temperature collection](https://doi.org/10.6084/m9.figshare.c.4488089.v1),
described by [Moll et al. (2019)](https://doi.org/10.1038/s41597-019-0208-1).
This acquisition writes only `datasets/external/open_guided_waves_confirmation/`.
The original source, raw banks, protocol, study and public summary are retained
with before/after byte hashes. Nothing is substituted into the old study.

## Frozen selection and roles

Every bank uses all 66 actually recorded unordered pitch-catch paths at native
10 MSPS, with the published 40 kHz excitation. No reciprocal direction or
missing waveform is fabricated.

| Role | State/cycle | Chronological 40 kHz indices | Nominal chamber temperatures |
|---|---|---|---|
| Healthy trajectory calibration | First healthy cycle, cooling | 84,88,...,156 | 58,56,...,22 C; nineteen blocks |
| Healthy confirmation test | Second healthy cycle, ascending | 181,221 | 30,50 C |
| Damage confirmation test | D04, D12, D16 and D24, each first ascending cycle | 20,60 for each state | 30,50 C |

The source protocol has 161 timestamps per cycle: ascent from 20 to 60 C in
0.5 C steps, then cooling. Indices and roles were chosen from that schedule,
before inspecting signals. Actual chamber readings are checked against nominal
setpoints within 0.25 C; the two measured surface temperatures are retained.
No waveform feature, damage index, result or plot is calculated by the downloader.
Schema inspection reads only shapes/datatypes and small condition/acquisition
metadata. Signal bytes are read solely for original-member CRC and SHA-256.

The nineteen healthy cooling blocks are reserved to calibrate **whole adaptive
trajectory maxima**, rather than treating individual correlated paths as
independent calibration examples. They are disjoint from the old healthy
20/40/60 C ascending fit banks and from the second-cycle healthy test banks.
The ten confirmation banks are disjoint from all eighteen previously analysed
OGW banks. They must remain unexamined by the compensator/gate implementation
until its protocol, parameters and source hashes are frozen.

There are nineteen temperature blocks, **not nineteen independent specimens**.
All come from the same plate, and nearby temperatures are correlated. Cooling
can differ from warming through thermal hysteresis and acquisition history;
these limitations must be carried into any nonparametric calibration or
exchangeability argument. The four defect-position labels remain reversible
surface-disc scatterers rather than permanent manufactured delaminations.

## Integrity, provenance and completion

The requested acquisition contains 29 banks, nominally 403,070,304 raw numeric
bytes. The independent `argus_manifest.json` is the completion authority: it
records each role/index/timestamp, actual temperatures, original member path,
archive URL, byte count, CRC32, raw SHA-256, and explicit completion/failure state.
Partial acquisitions cannot be relabelled complete.

The initial attempt encountered HTTP 403 on the official public download routes
before any new bank arrived. The incomplete manifest and failure are retained;
no old waveform was substituted. A later successful acquisition must be shown
by the separate manifest's complete 29-bank receipt before confirmation scoring.

The downloader imports the existing bounded HTTP-range/archive/HDF5 inspection
helpers read-only. It rejects full-archive responses, unsafe paths/links, illegal
storage/filter/type/allocation shapes and incompatible acquisition metadata.
Numeric files and manifests are atomically written inside the new directory.
Exact original geometry, article/license and Figshare metadata are copied into
the new metadata folder. Downloads do not execute publisher code or deserialize
models.

Publisher MD5 values cover whole multi-gigabyte archives, which are not fetched.
Their MD5 remains explicitly **unverified**. Selected original members have
verified ZIP CRC/length and locally computed SHA-256 with HTTPS provenance;
these do not authenticate a physical sensing device. The old-evidence hash
inventory is recomputed at completion and must match exactly.

```powershell
.venv\Scripts\python.exe scripts\download_ogw_confirmation.py
```

No waveform analysis or performance claim is made by this acquisition. An
eventual held-out evaluation will still be an offline reanalysis of one
published specimen, not a prospective ARGUS hardware experiment or a guarantee
of a finite-sample false-alarm rate under temperature dependence.
