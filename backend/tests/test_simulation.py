import numpy as np

from backend.app.hardware.devices import SimulationDevice
from backend.app.models.domain import Defect, Experiment
from backend.app.simulation.physics import AcousticSimulator


def test_simulation_reproducibility():
    defect = Defect(0.42, 0.61, 0.09, 0.07, 0.75, "cavity")
    experiment = Experiment(0.05, 0.12, 0.92, 0.84, 1_400, 4_200, 0.48, 0.12, "chirp")
    first = AcousticSimulator(seed=99).simulate(defect, experiment)
    second = AcousticSimulator(seed=99).simulate(defect, experiment)
    assert np.array_equal(first, second)
    assert np.std(first) > 0.001


def test_defect_changes_physical_response():
    simulator = AcousticSimulator(seed=3)
    experiment = Experiment(0.05, 0.05, 0.95, 0.95)
    signal = simulator.simulate(Defect(0.5, 0.5), experiment, add_noise=False)
    baseline = simulator.simulate_baseline(experiment)
    assert np.linalg.norm(signal - baseline) > 0.05


def test_simulation_acquisition_device_is_functional():
    simulator = AcousticSimulator(seed=41)
    truth = simulator.random_defect("easy")
    experiment = Experiment(0.05, 0.05, 0.95, 0.95, 1_200, 3_000, 0.48, 0.12, "chirp")
    device = SimulationDevice(simulator, truth)
    assert device.connect()["connected"] is True
    samples = device.acquire(experiment, simulator.sample_rate)
    assert samples.shape == (int(experiment.duration_s * simulator.sample_rate),)
    assert np.all(np.isfinite(samples))
