from __future__ import annotations

from abc import ABC, abstractmethod
import threading
import time
import secrets
from dataclasses import asdict

import numpy as np

from backend.app.models.domain import Defect, Experiment
from backend.app.simulation.physics import AcousticSimulator
from backend.app.hardware.protocol_v2 import (
    MAX_LINE_BYTES, PONG_LEGACY, PONG_V2, ProbeCapabilities, ProbeRequest,
    ProbeTimingCalibration, parse_frame, wire_line,
)


class AcquisitionDevice(ABC):
    name = "acquisition_device"

    def __init__(self) -> None:
        self.connected = False
        self.last_error: str | None = None

    @abstractmethod
    def connect(self, **kwargs) -> dict: ...

    def disconnect(self) -> dict:
        self.connected = False
        return self.status()

    @abstractmethod
    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray: ...

    def status(self) -> dict:
        return {"name": self.name, "connected": self.connected, "last_error": self.last_error}


class SimulationDevice(AcquisitionDevice):
    """Acquisition adapter for the same seeded digital twin used by the engine."""

    name = "simulation"

    def __init__(self, simulator: AcousticSimulator, truth: Defect) -> None:
        super().__init__()
        self.simulator = simulator
        self.truth = truth

    def connect(self, **kwargs) -> dict:
        self.connected = True
        self.last_error = None
        return self.status()

    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray:
        if not self.connected:
            raise RuntimeError("Simulation device is not connected")
        if sample_rate != self.simulator.sample_rate:
            raise ValueError("Simulation device sample rate must match its digital twin")
        return self.simulator.simulate(self.truth, experiment)


class UploadedSignalDevice(AcquisitionDevice):
    name = "wav_upload"

    def __init__(self) -> None:
        super().__init__()
        self._samples: np.ndarray | None = None
        self.connected = True

    def connect(self, **kwargs) -> dict:
        self.connected = True
        return self.status()

    def load(self, samples: np.ndarray) -> None:
        values = np.asarray(samples, dtype=np.float32).reshape(-1)
        if values.size < 8:
            raise ValueError("Uploaded signal is empty")
        self._samples = values

    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray:
        if self._samples is None:
            raise RuntimeError("No uploaded signal is loaded")
        samples, self._samples = self._samples, None
        return samples


class MicrophoneDevice(AcquisitionDevice):
    name = "microphone"

    def connect(self, **kwargs) -> dict:
        try:
            import sounddevice as sd

            sd.query_devices(kind="input")
            self.connected = True
            self.last_error = None
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
        return self.status()

    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray:
        if not self.connected:
            raise RuntimeError("Microphone is not connected")
        import sounddevice as sd

        frames = int(experiment.duration_s * sample_rate)
        recording = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
        return recording[:, 0]


class SerialProbeDevice(AcquisitionDevice):
    name = "serial_probe"
    arrival_likelihood_supported = False

    def __init__(self) -> None:
        super().__init__()
        self.port: str | None = None
        self._serial = None
        self._lock = threading.RLock()
        self.protocol_version: int | None = None
        self.capabilities: ProbeCapabilities | None = None
        self.timing_calibration: ProbeTimingCalibration | None = None
        self.last_acquisition_metadata: dict | None = None
        self.baudrate = 115200
        self.arrival_likelihood_supported = False

    def _read_line(self) -> bytes:
        raw = self._serial.readline(MAX_LINE_BYTES + 1)
        if raw:
            wire_line(raw)
        return raw

    @staticmethod
    def available_ports() -> list[dict]:
        try:
            from serial.tools import list_ports

            return [{"port": item.device, "description": item.description, "hardware_id": item.hwid} for item in list_ports.comports()]
        except Exception:
            return []

    def connect(self, **kwargs) -> dict:
        with self._lock:
            self.disconnect()
            try:
                import serial

                available = self.available_ports()
                port = kwargs.get("port") or (available[0]["port"] if available else None)
                if not port:
                    raise RuntimeError("No serial probe detected")
                if isinstance(kwargs.get("baudrate", 115200), bool):
                    raise ValueError("Serial baud rate must be an integer")
                self.baudrate = int(kwargs.get("baudrate", 115200))
                if not 9600 <= self.baudrate <= 2000000:
                    raise ValueError("Unsupported serial baud rate")
                self._serial = serial.Serial(port, self.baudrate, timeout=0.2, write_timeout=2)
                time.sleep(0.25)
                self._serial.reset_input_buffer()
                self._serial.write(b"PING\n")
                answer = self._read_line().rstrip(b"\r\n")
                if answer == PONG_V2:
                    self.protocol_version = 2
                    self._serial.write(b"CAPABILITIES\n")
                    self.capabilities = ProbeCapabilities.parse(self._read_line())
                    metadata = kwargs.get("timing_calibration")
                    if metadata is not None:
                        self.timing_calibration = ProbeTimingCalibration.from_metadata(metadata, self.capabilities)
                        if self.baudrate < 115200:
                            raise ValueError("V2 acquisition requires at least 115200 baud")
                        self.arrival_likelihood_supported = True
                elif answer == PONG_LEGACY:
                    self.protocol_version = 1
                    if kwargs.get("timing_calibration") is not None:
                        raise ValueError("Legacy post-excitation firmware cannot accept timing calibration")
                else:
                    raise RuntimeError("Probe did not provide a supported exact ARGUS protocol handshake")
                self.port = str(port)
                self.connected = True
                self.last_error = None
            except Exception as exc:
                self.disconnect()
                self.last_error = str(exc)
        return self.status()

    def disconnect(self) -> dict:
        with self._lock:
            if self._serial:
                try:
                    self._serial.write(b"STOP\n")
                except Exception:
                    pass
                finally:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
            self._serial = None
            self.connected = False
            self.protocol_version = None
            self.capabilities = None
            self.timing_calibration = None
            self.arrival_likelihood_supported = False
            self.last_acquisition_metadata = None
        return self.status()

    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray:
        with self._lock:
            if not self.connected or self._serial is None:
                raise RuntimeError("Serial probe is not connected")
            if self.protocol_version != 2 or self.capabilities is None or self.timing_calibration is None:
                raise RuntimeError(
                    "Arrival localization requires a concurrent, trigger-referenced v2 frame and explicit "
                    "device-specific operator timing/drive calibration evidence; legacy firmware and wire version alone are blocked."
                )
            # Validate every command field and current calibration before any
            # excitation request. Invalid requests never reach the actuator.
            request = ProbeRequest.build(experiment, sample_rate, self.capabilities, self.timing_calibration, secrets.token_hex(16))
            self.last_acquisition_metadata = None
            self._serial.reset_input_buffer()
            deadline = time.monotonic() + min(60.0, 5 + experiment.duration_s + request.total_samples * 56 * 10 / self.baudrate)

            def frame_lines():
                for _ in range(request.total_samples + 2):
                    raw = b""
                    while not raw:
                        if time.monotonic() >= deadline:
                            raise ValueError("Timed out before a complete triggered serial frame")
                        raw = self._read_line()
                    yield raw

            try:
                self._serial.write(request.command())
                frame = parse_frame(frame_lines(), request, self.capabilities, self.timing_calibration)
            except Exception as exc:
                self.disconnect()
                self.last_error = f"V2 acquisition rejected: {exc}"
                raise RuntimeError(self.last_error) from exc
            self.last_acquisition_metadata = frame.metadata
            return frame.samples

    def status(self) -> dict:
        return {**super().status(), "port": self.port, "available_ports": self.available_ports(),
                "arrival_likelihood_supported": self.arrival_likelihood_supported,
                "protocol_version": self.protocol_version,
                "capabilities": asdict(self.capabilities) if self.capabilities else None,
                "timing_calibration": asdict(self.timing_calibration) if self.timing_calibration else None,
                "acquisition_contract": "concurrent_triggered_frame_with_operator_calibration" if self.protocol_version == 2 else "legacy_post_excitation_decay_only_not_arrival_aligned",
                "calibration_provenance": "operator_attestation_and_external_digest; not host-certified bench validation",
                "last_frame_contract_checked": self.last_acquisition_metadata is not None}


def discover_devices() -> dict:
    serial = SerialProbeDevice()
    microphone = MicrophoneDevice()
    return {
        "simulation": {"name": "simulation", "connected": True, "available": True},
        "wav_upload": {"name": "wav_upload", "connected": True, "available": True},
        "serial_probe": serial.status(),
        "microphone": {**microphone.status(), "available": True},
    }
