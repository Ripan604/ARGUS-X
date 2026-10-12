# ARGUS ESP32 v2 reference probe

The v2 sketch records the receiver while generating a sampled DAC sine/chirp
under one monotonic clock. It includes 16 pretrigger samples, a GPIO26 trigger
marker, per-sample ADC-call timestamps and DAC codes, complete ordered frames,
integrity checks and explicit STOP/overrun status. It replaces the earlier
excite-then-record example, whose missing early arrivals made it incompatible
with the backend's arrival model.

This is an implementation reference for a **classic ESP32** with GPIO25 DAC and
GPIO34 ADC. The full sketch and portable protocol compile/run against host
Arduino mocks; that result is not an ESP32 board-target or physical timing test.
No board flashing or measured sensor campaign is represented here. An isolated
official board-build preparation used verified Arduino CLI 1.5.1 and requested
stable Espressif core 3.3.12 for `esp32:esp32:esp32`. Core/toolchain installation
did not finish within the bounded attempt; no board compile command ran or
binary was generated. See `output/release/probe-v2-board-build.json` for the
receipt. Even a successful board compile could not validate circuit or timing.

## Wiring and bounds

| Function | Pin | Required connection |
|---|---:|---|
| Source | GPIO25 DAC | AC-coupled high-impedance external amplifier input; never power a transducer directly |
| Receiver | GPIO34 ADC | Protected, buffered, band-limited and biased 0-3.3 V analog input |
| Trigger marker | GPIO26 | Logic-only timing output for an oscilloscope/logic analyser |
| Polled STOP | GPIO27 | Normally high with pull-up; ground to latch waveform off |
| Status | GPIO2 | Status LED where provided by the board |
| Ground | GND | Common ground for the board, sensor and amplifier |

Use a protected high-impedance receiver front end and an appropriate antialias
filter. The external amplifier must have measured safe gain/current/voltage
limits. The DAC is biased at code 128; accepted amplitude is at most 0.60 of
127 DAC codes, not a certified force, pressure, power or current limit. The
source's biased idle is safe only with the specified AC-coupled driver input.
GPIO27 is polled software, not an independent physical power interlock.

Requests are restricted to 1000-16000 Hz sample rate, 20-250 ms posttrigger
windows, 4096 total samples including pretrigger, 100-6000 Hz source band and
end frequency <= 0.40 of sample rate. Only CHIRP and TONE_BURST are supported;
the latter requires equal endpoints. Unsupported coded, Ricker, multisine and
notched families are rejected before driving.

The 10 ms maximum burst, Tukey alpha 0.45 and phase convention mirror the
supported software excitation. Quantized DAC commands are recorded, not
assumed to equal measured actuator motion. A requested maximum rate may fail
with OVERRUN on a particular board; unsuccessful captures supply no inference
samples. Do not relabel the requested rate as a measured hardware clock.

## Protocol and host enablement

Serial is 115200 baud, 8-N-1, newline-terminated ASCII. `PING` responds with
`PONG,ARGUS_PROBE,2`; `CAPABILITIES` reports a chip-specific identifier and
supported acquisition envelope. `STOP` latches drive off; `RESET_STOP` is refused
while GPIO27 remains low. Legacy EXPERIMENT/READ/EXCITE commands are unsupported.

```text
EXPERIMENT2 <id32hex> <experiment_sha256> <fstart> <fend> <amplitude> <window_us> <CHIRP|TONE_BURST> <requested_rate> <pretrigger_count>
```

The buffered response consists of BEGIN2 metadata, indexed DATA2 records with
timestamp/ADC/DAC fields, and an END2 count/checksum/status. Source excitation
overlaps acquisition; transmission happens after waveform disable. The exact
17-field header and FNV grammar are in [PROBE_V2_DESIGN.md](../../docs/PROBE_V2_DESIGN.md).
The full Experiment hash is echoed for host binding; it is not sensor
authentication. The chip suffix identifies a board for operator calibration
binding and is not a cryptographic identity.

The host refuses localization actuation without a current device-specific
operator timing/drive declaration and external evidence digest. Version 2 alone
does not satisfy that gate. The declaration must come from an actual external
clock/trigger/transfer bench and match the board and acquisition rate. The host
checks the declaration and frames but does not independently certify the bench.
Frame rejection cannot substitute for physical transfer/calibration measurements.

## Reproducible host checks

```powershell
powershell -ExecutionPolicy Bypass -File firmware/esp32/tests/run_host_tests.ps1
```

This runs g++ C++17 property tests and compiles the entire `.ino` against
`tests/Arduino.h` mocks with warnings as errors. It exercises clock deadlines,
bounded source sequence, unsupported/malformed requests, concurrent drive/capture,
pretrigger/quiet tail, complete frames/checksum, STOP, overrun and clock rollover.
`output/release/probe-v2-host-fixture.txt` contains generated mock samples and
virtual timestamps, not a physical recording.

See [PROBE_V2_DESIGN.md](../../docs/PROBE_V2_DESIGN.md) for the concrete apparatus,
analog/clock gaps, worked geometry and physical acceptance checklist. No
certified NDE or structural-safety result is implied by compile/tests.
