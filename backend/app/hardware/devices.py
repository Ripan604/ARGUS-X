from __future__ import annotations

from abc import ABC, abstractmethod
import threading
import time

import numpy as np

from backend.app.models.domain import Defect, Experiment
from backend.app.simulation.physics import AcousticSimulator


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

    def __init__(self) -> None:
        super().__init__()
        self.port: str | None = None
        self._serial = None
        self._lock = threading.Lock()

    @staticmethod
    def available_ports() -> list[dict]:
        try:
            from serial.tools import list_ports

            return [{"port": item.device, "description": item.description, "hardware_id": item.hwid} for item in list_ports.comports()]
        except Exception:
            return []

    def connect(self, **kwargs) -> dict:
        try:
            import serial

            port = kwargs.get("port") or (self.available_ports()[0]["port"] if self.available_ports() else None)
            if not port:
                raise RuntimeError("No serial probe detected")
            self._serial = serial.Serial(port, int(kwargs.get("baudrate", 115_200)), timeout=2)
            time.sleep(0.25)
            self._serial.reset_input_buffer()
            self._serial.write(b"PING\n")
            answer = self._serial.readline().decode("utf-8", errors="replace").strip()
            if "PONG" not in answer:
                raise RuntimeError(f"Probe did not answer PING (received {answer!r})")
            self.port = str(port)
            self.connected = True
            self.last_error = None
        except Exception as exc:
            if self._serial:
                self._serial.close()
            self._serial = None
            self.connected = False
            self.last_error = str(exc)
        return self.status()

    def disconnect(self) -> dict:
        if self._serial:
            try:
                self._serial.write(b"STOP\n")
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.connected = False
        return self.status()

    def acquire(self, experiment: Experiment, sample_rate: int) -> np.ndarray:
        if not self.connected or self._serial is None:
            raise RuntimeError("Serial probe is not connected")
        command = (
            f"EXPERIMENT {experiment.frequency_start_hz:.0f} {experiment.amplitude:.3f} "
            f"{experiment.duration_s * 1000:.0f} {experiment.waveform.upper()} {sample_rate}\n"
        )
        with self._lock:
            self._serial.reset_input_buffer()
            self._serial.write(command.encode("ascii"))
            samples: list[float] = []
            deadline = time.monotonic() + max(4.0, experiment.duration_s * 8)
            while time.monotonic() < deadline:
                line = self._serial.readline().decode("ascii", errors="ignore").strip()
                if line == "END":
                    break
                if line.startswith("DATA,"):
                    fields = line.split(",")
                    try:
                        samples.append(float(fields[-1]))
                    except ValueError:
                        continue
                elif line.startswith("ERROR"):
                    raise RuntimeError(line)
            if len(samples) < 8:
                raise RuntimeError("Probe returned no usable samples")
            values = np.asarray(samples, dtype=np.float32)
            if np.max(np.abs(values)) > 4:
                values = (values - np.median(values)) / 2048.0
            return values

    def status(self) -> dict:
        return {**super().status(), "port": self.port, "available_ports": self.available_ports()}


def discover_devices() -> dict:
    serial = SerialProbeDevice()
    microphone = MicrophoneDevice()
    return {
        "simulation": {"name": "simulation", "connected": True, "available": True},
        "wav_upload": {"name": "wav_upload", "connected": True, "available": True},
        "serial_probe": serial.status(),
        "microphone": {**microphone.status(), "available": True},
    }
