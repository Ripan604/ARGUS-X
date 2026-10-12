# Open Guided Waves measured-data source audit

**Date:** 8 October 2026. **Scope:** a bounded native-frequency subset of OGW
dataset #2, downloaded from its official Figshare collection for offline
research. No ARGUS apparatus was exercised and no acquired signal was simulated.

## Source and permitted interpretation

Dataset #1's official download page returned HTTP 403, so it was not treated as
an available acquisition source. The accessible alternative is the authors'
temperature extension, [OGW Figshare collection 4488089](https://api.figshare.com/v2/collections/4488089/articles?page_size=100),
described in Moll et al., *Temperature affected guided wave propagation in a
composite plate complementing the Open Guided Waves Platform*, Scientific Data
6:191 (2019), DOI [10.1038/s41597-019-0208-1](https://doi.org/10.1038/s41597-019-0208-1).
The original article XML is retained from the
[public scholarly repository](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6778066/fullTextXML).

The plate is 500 x 500 x 2 mm quasi-isotropic CFRP, with twelve co-bonded
piezoelectric transducers. Excitation uses five-cycle Hann-windowed sinusoids;
the selected bank is 40 kHz and 10 MSPS. Experiments use 20-60 C chamber ramps
in 0.5 C steps: two healthy cycles and one cycle per reference-damage position.
The four location labels represent a surface-mounted aluminium disc attached
with tacky tape. It remains present during each measurement bank, but is a
reversible scattering surrogate, not a manufactured cavity or real delamination.
These specimen/method/coordinate facts come from the primary paper's Methods
and Tables 1-3. Exact reported geometry is saved in `metadata/geometry.json`.

This is measured ultrasonic response evidence on a separate instrument. It must
not be resampled to 16 kHz and relabelled as validation of ARGUS's audio-range
ESP32 probe. Offline replay reveals recorded feasible paths as the policy asks
for them; it does not perform new adaptive physical acquisitions.

## Original records, licenses and bounded downloads

| State | Official article metadata | Original archive bytes |
|---|---|---:|
| Healthy | [8108297](https://api.figshare.com/v2/articles/8108297) | 53,609,050,314 |
| D04 | [8107889](https://api.figshare.com/v2/articles/8107889) | 26,804,589,215 |
| D12 | [8107886](https://api.figshare.com/v2/articles/8107886) | 26,804,610,548 |
| D16 | [8107883](https://api.figshare.com/v2/articles/8107883) | 26,804,608,838 |
| D24 | [8107880](https://api.figshare.com/v2/articles/8107880) | 26,804,598,535 |

Every official article API declares the **data license CC0** and supplies its
original archive filename, download URL, byte length and MD5. Each original
JSON response is retained locally. The paper's text is **CC BY 4.0**; article
and data licensing are recorded separately. Attribution is retained even though
the dataset is dedicated to the public domain. Do not substitute a third-party
model, modified archive or an AI-generated signal for these originals.

Fetching all archives would exceed 160 GB. Their HDF5 members are stored
uncompressed inside ZIP/ZIP64, allowing ordinary public HTTP byte-range reads.
The downloader requires HTTP 206 and an exact Content-Range before accepting
any body, reads the central directory and selected bounded members, and refuses
a server response that would download the whole archive.

The selection was fixed **before waveform analysis** from the publisher's
thermal schedule: ascending-ramp indices 0, 40, 80 for each damage state, and
0, 40, 80 plus 161, 201, 241 for the two healthy cycles. These correspond to
nominal chamber setpoints 20, 40 and 60 C. They are not selected by damage-index
strength or localization success. Actual measured chamber and both surface
temperatures are preserved, and setpoint agreement is checked within 0.25 C.
This is a protocol-index subset, not a claim to select the closest measured
surface temperature across every file in the full collection.

The requested subset comprises **18 full banks**, each 13,898,976 bytes, about
250 MB total numeric data. `argus_manifest.json` is the completion authority:
its accepted file list, failures and transfer count describe what actually
finished. All eighteen banks completed; 250,181,568 raw numeric bytes, every
signal finite, original member CRC and actual SHA-256 rechecked after download.
`download_verification.json` retains the per-condition receipt.
The six healthy banks support separation of the first ascending cycle
as baseline/development and the second as independent test; cycles must not be
mixed while fitting thresholds or calibration. All measurements remain from
one specimen, which limits generalization and statistical independence.

## Actual numeric schema inspected

The first accepted healthy bank has these native datasets:

| HDF5 path | Shape | Meaning |
|---|---:|---|
| `pitchcatch/catch` | 66 x 13,108, float64 | Receiver voltage histories |
| `pitchcatch/pitch` | 66 x 13,108, float64 | Recorded source histories |
| `command/pitchcatch/channels` | 66 x 2, uint8 | Zero-based source/receiver pairs |
| `command/pitchcatch/sampling_frequency` | 1 | 10,000,000 Hz |
| `command/pitchcatch/signal_frequency` | 1 | 40,000 Hz |
| `command/pitchcatch/signal_cycles` | 1 | Five cycles |
| `command/pitchcatch/signal_data` | 1 x 5,001 | Declared excitation waveform |
| `CTC/Temperature`, `CTC/Humidity` | 1 each | Chamber conditions |
| `Temperature/values` | 2 | Bottom-left/top-left surface temperatures |
| `timestamp` | 1 | Original numeric measurement timestamp |

There are **66 unordered pairs (i < j)**, not 132 separately observed directions.
Reciprocal measurements must not be invented by duplicating these records.
The first file reports chamber 20.0 C and surface [21.236,21.099] C; its nominal
40 C counterpart reports chamber 40.1 C and surface [41.156,41.068] C. Those
differences are measured nuisance variation, not incorrect labels to overwrite.
Per-file `.schema.json` files retain shapes, primitive datatypes and small
numeric metadata without loading large signal arrays during source inspection.

Sensor positions are fixed, in metres: T1-T6 use x=[.450,.370,.290,.210,.130,.050]
at y=.470; T7-T12 use the same x values at y=.030. The primary-paper location
labels are D04=(.065,.400), D12=(.195,.330), D16=(.335,.260), D24=(.450,.190).
These are independently published truth for final scoring, not values learned
from test waveforms. A planning/localization procedure must not inspect a
case's label while selecting its next measurement path.

## Integrity and safety checks

The downloader in [download_open_guided_waves.py](../scripts/download_open_guided_waves.py)
uses a 900 MiB default transfer budget, a 64 MiB member/read/allocation cap and
bounded archive/HDF5 object counts. Only selected `.h5` files are written;
downloaded MATLAB/Python code is never extracted or executed. Archive traversal,
absolute/drive paths, symlinks, encryption, unsupported compression and excessive
expansion are rejected. Output paths must resolve inside the dataset directory.
HDF5 external/soft links and external/virtual dataset storage are refused;
object/reference datatypes and unbounded attributes are not read.
Nine focused regression cases passed, covering archive path/symlink rejection,
refusal to read a whole-archive response, and HDF5 external-link, variable-length
signal and oversized-array rejection. These checks are bounded input controls,
not a guarantee against every native HDF5-library vulnerability.

Each complete member is checked against the ZIP central-directory **CRC32 and
byte length**, including on resume. Its actual raw **SHA-256** is written to
the manifest and the original member path and archive URL are retained. The
publisher's MD5 applies to an entire archive that was not downloaded; therefore
**whole-archive MD5 is explicitly unverified**. Partial-member CRC/SHA plus HTTPS
provenance provide reproducible local consistency, not a verified whole-archive
cryptographic checksum or sensor-authenticity guarantee. Do not erase this
distinction from release reports.

## Reproduction and evaluation boundary

```powershell
.venv\Scripts\python.exe scripts\download_open_guided_waves.py --frequency-khz 40 --selection protocol-temperature --max-download-mib 900
.venv\Scripts\python.exe scripts\download_open_guided_waves.py --verify-only
.venv\Scripts\python.exe -m pytest scripts\test_download_open_guided_waves.py -q -o addopts=""
```

Data, original metadata and manifests live under
`datasets/external/open_guided_waves/`, excluded from source-control payloads.
The evaluation should verify file SHA-256 before loading, retain native sampling
and measured source/receiver pairs, report matched-temperature versus fixed
baseline behavior, and keep independent healthy tests for false alarms.

Comparisons between adaptive, cyclic, random and full-bank replay should use
the same recorded opportunities, common budgets and independent policy seeds.
Damage labels are for scoring only; any learned likelihood/threshold uses only
declared development evidence. Four reference locations on one plate cannot
establish arbitrary hidden-defect localization or cross-specimen reliability.
Path-level repeats within a bank are not independent specimens, and changing
temperature does not manufacture a new damage location. Retain all failures,
false alarms, rejected observations and large-error cases in the report.
