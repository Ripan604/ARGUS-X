# ARGUS v2 concurrent reference probe and enabling apparatus

7 October 2026. This document separates implemented firmware and host/mock
checks from the physical apparatus and metrology still to be built and measured.
No board was flashed and no physical waveform was acquired for these changes.

## Technical purpose and implemented boundary

The controller's direct and bistatic arrival models require an observation
window tied to the excitation onset. The earlier ESP32 sketch generated up to
12 ms of excitation and only then recorded the response. That sequence omitted
early arrivals and assigned a different clock origin from the inference model.
The earlier host protocol also did not validate declared counts, ordered indices,
clock times or excitation endpoints.

The v2 sketch computes the supported excitation before acquisition, collects
16 pretrigger samples, and changes the source DAC during the same timed loop in
which it records the receiver ADC. It reports per-sample acquisition-call times
and source DAC codes. It returns unsuccessful status on deadline overrun or stop
and disables the waveform before transmitting the buffered result. The host
can now reject inconsistent or unsupported acquisitions before defect inference.
These are implemented control and data-integrity effects; they do not establish
physical localization accuracy or patent novelty.

`argus_protocol.h` contains portable parsing, hard bounds, rational sample
deadlines, excitation quantization and checksum logic. `argus_probe.ino` applies
that logic to classic ESP32 GPIO25 DAC and GPIO34 ADC through Arduino core 2.x
APIs. Other ESP32 variants without this DAC/pin layout are outside this reference.
An Arduino mock compiles the entire sketch on the host. An isolated official
board-toolchain installation was subsequently attempted with Arduino CLI 1.5.1
and stable Espressif core 3.3.12 for `esp32:esp32:esp32`. The CLI ZIP hash was
verified, but the core installation did not finish within the bounded attempt.
Its two compiler archives alone require over 1 GiB before the chip libraries and
core. No board compile command ran and no board binary exists. The receipt is
`output/release/probe-v2-board-build.json`; isolated CLI/downloads remain under
`tmp/toolchains/argus-v2`. No global tool installation was changed.

## Apparatus drawing specification

Figure A should show the following numbered elements and connections:

1. Rectangular plate under investigation, with measured width and height.
2. Contact exciter at source position S, connected to an external amplifier.
3. Contact piezoelectric receiver at R, connected to a buffered analog front end.
4. Source DAC on classic ESP32 GPIO25, AC-coupled into the amplifier input.
5. Receiver front end, biased near half the ADC range, protected/clamped and
   band limited, connected to GPIO34. Show a common electrical ground.
6. Common monotonic microsecond counter controlling DAC updates and recording
   ADC-call timestamps. Show separate arrows to DAC and ADC; the calls are
   sequential within each sample interval, not simultaneous converter apertures.
   GPIO26 supplies a logic trigger marker for external timing instrumentation.
7. A STOP input at GPIO27 and an independent actuator-supply cutoff. The GPIO
   input is polled software; the independent physical cutoff is a proposed circuit.
8. A USB serial link to the laptop controller, structural probability grid,
   correlated speed/timing covariance, feasible-action bank and observation gate.
9. A measured positioning fixture or manual coordinate marks for S and R.

Figure B should show 16 idle pretrigger samples, a recorded trigger marker,
a windowed source burst while ADC acquisition continues, a quiet receiver tail,
waveform disable, and buffered frame transmission. Mark the difference between
the DAC-call trigger and actual electrical/ADC aperture timing, which must be
measured externally.

Figure C should show alternative direct-reference paths of 0.18, 0.36 and
0.54 m, the correlated (velocity, delay) covariance, a chosen diagnostic
bistatic path, and the controller selecting the reference that reduces its
full-grid propagation prediction variance. Distinct reference lengths give
different observation directions; repeating one length cannot independently
identify both propagation velocity and instrument delay.

## Analog and mechanical embodiment proposed for construction

Use a 600 x 400 mm plate, a fixed coordinate origin, an independently measured
source/receiver position and a known healthy reference arrangement. Material,
thickness, boundary fixtures, temperature, exciter and receiver part numbers,
front-end transfer response, coupling layer and gain must be recorded from the
actual apparatus. The default software word `composite` and effective speed
180 m/s are simulator settings, not a physical material specification.

GPIO25 is a low-current 8-bit DAC output. It must drive an AC-coupled,
high-impedance amplifier input, never a speaker, motor or low-impedance piezo
directly. The reference idle code is 128. For amplitude a, the requested source
code is round(128 + 127 a u[n]), with a <= 0.60 and |u[n]| <= 1. The maximum
nominal excursion is therefore 76 DAC codes from idle. This bound is on digital
drive commands. It is not a measured force, acoustic pressure, supply current,
energy, power or transducer displacement bound. Establish external amplifier
gain, voltage/current clamps and the permissible excitation from the actual
specimen/transducer specification before energizing it.

A piezoelectric receiver requires a high-impedance buffer, input protection,
an appropriate antialias filter and bias into the 0-3.3 V ADC range. ESP32 ADC
offset, nonlinearity, saturation, clock drift and DAC transfer characteristics
must be measured rather than inferred from their bit depths. A direct electrical
or healthy-panel transfer reference must justify the host's normalized model
units. The affine raw-code conversion (raw - 2048)/2048 alone does not characterize
the acoustic transfer function or coupling. A measured receiver reference and
operator calibration declaration must be retained separately.

Use a mechanical source/receiver fixture where possible. If manually placed,
record the measured coordinates and placement uncertainty for each observation.
A camera overlay assists placement but does not certify absolute probe position.
No robotic pose or force-controlled coupling is implemented in this embodiment.

## Frozen version 2 wire contract

All lines are ASCII, newline terminated. Identity/hash fields are lowercase
hexadecimal. Firmware supports `PING`, `CAPABILITIES` (aliases `CAPS`, `STATUS`),
`STOP`, `RESET_STOP`, and the v2 experiment command. Legacy `EXPERIMENT`,
`EXCITE`, `READ` and unsupported waveform names are rejected before driving.

```text
PING
PONG,ARGUS_PROBE,2

CAPABILITIES
CAPS,2,ESP32_DAC25_ADC34_<12lowerhex_chip_id>,16000,4096,12,concurrent_triggered,DAC8_SAMPLED_SINE,CHIRP|TONE_BURST,16

EXPERIMENT2 <id32hex> <experiment_sha256> <fstart> <fend> <amplitude> <window_us> <CHIRP|TONE_BURST> <requested_rate> <pretrigger_count>

BEGIN2,<id>,<hash>,<total_count>,<requested_rate>,<adc_bits>,<drive_family>,<waveform>,<trigger_index>,<trigger_time_us>,<fstart>,<fend>,<amplitude>,<window_us>,<burst_us>,<drive_start_us>,<drive_end_us>
DATA2,<index>,<elapsed_us>,<adc_raw>,<drive_code>
END2,<id>,<total_count>,<fnv1a32_hex>,<status>,<maximum_deadline_lateness_us>
```

The full Experiment hash binds geometry and excitation metadata on the host;
firmware echoes the supplied hash rather than calculating or authenticating it.
The capability device identifier includes the low 48 bits of ESP.getEfuseMac(),
allowing the host to bind the operator's bench declaration to a specific chip.
It is not an authenticated or unforgeable sensor identity. FNV-1a detects transfer inconsistency;
it is not a cryptographic message-authentication or provenance guarantee.

The checksum starts at 2166136261 and processes exact ASCII lines
`index,elapsed_us,adc_raw,drive_code\n` with XOR then multiplication by 16777619,
modulo 2^32. The host verifies the echoed id, hash and every declared command
parameter, exact ordered count and checksum before accepting a frame.

`elapsed_us` is a wrapping-clock difference from the first ADC-call timestamp.
It must start at zero and strictly increase. `trigger_time_us` is the trigger-call
start offset at the pretrigger boundary, immediately before setting GPIO26 high
and writing the source DAC. `drive_start_us` uses that same scheduling marker;
`drive_end_us` is the call time at which the DAC returns to idle after its burst.
These timestamps describe firmware call scheduling, not the hardware converter
aperture, electrical output settling or transducer-force onset.
GPIO26 returns low at the burst-end call and when the source is disabled; its
external electrical edges support later timing measurements and remain subject
to the actual digitalWrite/DAC/ADC call latencies.

## Supported excitation and clock constraints

- Requested rate: 1000-16000 Hz. This is a requested rate, not a claimed measured
  hardware rate. Each sample reports its actual call-time offset.
- Acquisition window after trigger: 20000-250000 microseconds. The total buffer
  is 16 + round(window_us * requested_rate / 1000000), at most 4096 samples.
- Source band: 100-6000 Hz, end >= start and end <= 0.40 * requested_rate.
  This conservative digital margin does not replace an analog antialias filter.
- Supported source families: CHIRP and TONE_BURST. The latter requires identical
  start/end frequencies. Ricker, multisine, coding and spectral notches are
  explicitly unsupported by this hardware reference.
- Burst sample count: max(16, round(min(10000, 0.22 * window_us) * rate / 1000000)).
  Windowing uses Tukey alpha 0.45. CHIRP uses linear frequency sweep with cosine
  initial phase zero and t1=(burst_samples-1)/rate; TONE_BURST uses sine phase.
- Rational deadline offsets floor(index * 1000000 / requested_rate) avoid the
  old fixed 62 microsecond step masquerading as an exact 16 kHz clock.
- Deadline lateness greater than floor(1000000/(4 * rate)), with minimum 2 us,
  yields OVERRUN and disables the waveform. No missing samples are invented.
  At 16 kHz this deadline tolerance is 15 us. A board may legitimately fail
  at its advertised maximum request rate; the host must then use a measured
  supported rate instead of accepting the failed capture.

At each tick the sketch writes the prepared DAC code and then starts the ADC
read. Source and receiver acquisition overlap throughout the source burst.
The sequential per-tick call order is retained in the description. All sine and
envelope computations occur before the timing loop. Serial transmission occurs
after the source is disabled, so serial baud rate does not determine capture
rate. Long frame transmission time still requires a sufficiently bounded host
deadline; it cannot be silently truncated into an accepted window.

STOP and the active-low GPIO27 input latch future drive off and are polled
during waiting/acquisition. `RESET_STOP` is refused while the input is active.
This polling implementation does not guarantee interrupt latency or protection
against CPU failure. A physical actuator-supply interlock remains necessary
where that protection is required. The waveform returns to biased DAC idle,
which is safe only with the declared AC-coupled amplifier circuit.

## Concrete enabling example, not an acquired measurement

For the 600 x 400 mm coordinate system, place a proposed reference source at
normalized (0.05, 0.08) and receiver at (0.35, 0.08). These correspond to
(30,32) mm and (210,32) mm, a direct reference path of 180 mm. A second reference
(0.05,0.50) to (0.65,0.50) has a 360 mm path; a third (0.05,0.92) to
(0.95,0.92) has a 540 mm path. Their placements and uncertainty require actual
independent measurement.

Command a 1200-3000 Hz CHIRP, amplitude 0.28, window 120000 us, rate 16000 Hz
and 16 pretrigger samples. The portable logic requests 1936 total samples,
including 1920 after the trigger, and a 160-sample/10000 us source burst.
Record actual call timestamps and the quantized source sequence. After a
bench-calibrated, complete frame is accepted, align the trigger and normalize
the receiver under the host acquisition contract. Obtain the reference delay
from the known excitation. Update the correlated speed/timing block using
that one scalar observation; use uniform structural likelihood for calibration.

For the purely illustrative simulator values v=180 m/s and t0=0.8 ms, the three
direct arrivals are 1.8, 2.8 and 3.8 ms after the declared trigger. These are
worked predictions, not measured arrivals. The v2 window includes them; the
earlier excite-then-record sketch started acquisition after such early arrivals.

The task-conditioned reference selector then estimates how each candidate
would change propagation variance across all structural grid cells for the
pending diagnostic geometry. The chosen accepted reference updates covariance
and forward-model means; the controller recomputes the subsequent physical
diagnostic action. Its eventual posterior update must use the actual diagnostic
waveform, with quality/model-support gates, and fresh verification before a
confident stop. A reference action alone never validates defect location.

## Patent-strengthening acceptance checklist

| Acceptance condition | Evidence status |
|---|---|
| Distinguish single reference rank-one update from identifying two unknowns | Implemented numerical regression; hardware not established |
| Rank varied reference lengths by their effect on the pending diagnostic's full-grid propagation variance | Implemented software and synthetic study; scope is propagation prediction |
| Feed accepted reference means/covariance back into later physically feasible action choice | Implemented controller path; actual apparatus campaign pending |
| Capture source/receiver concurrently under recorded call-time origin | Implemented v2 sketch; host/mock demonstration only |
| Bind actual declared family/endpoints, timestamps, DAC sequence and complete count to the action | Implemented protocol and host contract; transfer/clock bench pending |
| Reject missing, reordered, corrupt, stopped or overrun frames before fusion | Host/portable regression; not sensor authenticity |
| Reference acquisition cannot supply structural defect likelihood | Implemented uniform calibration likelihood |
| Fresh diverse quality-supported verification controls confident stop | Implemented controller check; empirical coverage pending |
| Measure trigger-to-DAC/ADC latency and clock drift on the intended board | Pending physical bench with external timing instrument |
| Measure transfer/antialias response, gain, noise, clipping and coupling | Pending physical bench |
| Blind specimen/location-held-out comparison at equal costs and budgets | Pending physical campaign |
| Map narrow apparatus/control limitations against closest prior art | Professional review pending; no novelty asserted |

The hardware/calibration portions cannot be labelled experimentally enabled
solely because a portable compiler accepts the code. Preserve the actual circuit
revision, firmware checksum, board identity record, external timing captures,
operator declaration, raw waveforms and source/receiver metrology with the
later physical study.

## Host verification actually executed

```powershell
powershell -ExecutionPolicy Bypass -File firmware/esp32/tests/run_host_tests.ps1
```

The available g++ compiler successfully compiled both portable protocol tests
and the complete `.ino` sketch against `tests/Arduino.h`, with C++17, warnings,
pedantic checking and warnings as errors. The portable tests exercise strict
numeric parsing, bounds, unsupported-family rejection, rational rate deadlines,
source code limits and checksum sensitivity. The sketch mock exercises source
drive during receiver acquisition, pretrigger/quiet windows, complete ordered
frames/checksum, active STOP latch, missed-deadline failure and micros rollover.

`output/release/probe-v2-host-fixture.txt` is a deterministic mock frame for
host-parser integration. It contains generated ADC values and virtual clock
times; it is explicitly not a sensor recording. No board compile, flashing,
oscilloscope capture, measured vibration or blind specimen inspection occurred.
