# Physical probe and acquisition

Simulation always remains available. Physical sessions accept:

- validated WAV uploads up to 10 MB;
- browser microphone capture encoded to PCM WAV;
- a local OS microphone through `sounddevice`;
- an ESP32 serial probe through `pyserial`.

Disconnected hardware is reported as unavailable rather than crashing the application. `GET /devices` lists detected serial ports. The detailed ESP32 wiring and protocol are in `firmware/esp32/README.md`.

## Physical coordinate workflow

The default panel is 600 × 400 mm. The backend converts normalized probe coordinates to physical distances for propagation; the UI displays both. Camera Align asks for four panel corners in top-left, top-right, bottom-right, bottom-left order, solves an eight-parameter projective homography, and projects the next probe/estimated defect onto the video.

## Safety

Use a transistor/MOSFET driver and a separate actuator supply. Never power a motor or low-impedance speaker from an ESP32 GPIO. Clamp and bias analog sensor signals to the ESP32 ADC range. This reference hardware is not certified for structural safety decisions.
