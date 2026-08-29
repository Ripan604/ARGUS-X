# ARGUS ESP32 reference probe

This firmware drives a small exciter and reads a piezo/analog vibration sensor. It is a safe starting point, not a universal analog front end.

## Wiring

| Function | ESP32 pin | Connection |
|---|---:|---|
| Exciter control | GPIO 25 | Input of a transistor/MOSFET driver; never drive a motor or speaker directly from the GPIO |
| Analog sensor | GPIO 34 | Conditioned 0–3.3 V output from piezo/accelerometer front end |
| Status | GPIO 2 | On-board LED on common dev boards |
| Ground | GND | Common ground for ESP32, driver, and sensor |

For a piezo disc, use a high-impedance buffer, bias the signal around 1.65 V, clamp it to 0–3.3 V, and add input protection. For a vibration motor, include a flyback diode. Power actuators from a suitable external supply.

Compile with the ESP32 Arduino core 2.x. The reference uses `ledcSetup`/`ledcAttachPin`; ESP32 Arduino core 3.x renamed parts of the LEDC API, so either select a 2.x board package or adapt those two calls.

Serial settings: 115200 baud, 8-N-1, newline-terminated commands. `EXPERIMENT <frequency_hz> <amplitude_0_to_1> <duration_ms> <IMPULSE|SINE|CHIRP> <sample_rate>` returns `BEGIN`, indexed `DATA`, and `END` lines. Samples are buffered before transmission, so 16 kHz acquisition is possible even though text transmission takes longer than real time.
