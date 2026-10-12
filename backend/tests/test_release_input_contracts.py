import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.schemas.api import CreateSessionRequest, ProbeMeasurementRequest, ResearchJobRequest
from backend.app.services.session_manager import SessionManager


@pytest.mark.parametrize('override', [
    {'candidate_count': 257}, {'top_hypotheses': 401},
    {'planner_beam_width': 33}, {'planner_rollout_samples': 65},
    {'forward_cache_size': 65_537}, {'maximum_duration_s': 3},
    {'sample_rate': 384_000, 'signal_duration': 2},
])
def test_importable_configuration_has_resource_bounds(override):
    with pytest.raises(ValueError):
        ArgusConfig(**override)


@pytest.mark.parametrize('samples', [[float('nan')]*8, [float('inf')]*8])
def test_probe_schema_rejects_nonfinite_samples(samples):
    with pytest.raises(ValidationError):
        ProbeMeasurementRequest(session_id='session',node_id='phone-1',sample_rate=16_000,samples=samples)


@pytest.mark.parametrize('metadata', [{'x':'a'*1025}, {'x':[1]*129}, {'x': {'x': {'x': {'x': {'x': 1}}}}}, {'x': float('inf')}])
def test_research_metadata_is_bounded(metadata):
    with pytest.raises(ValidationError):
        ResearchJobRequest(job_type='benchmark',parameters=metadata)


def test_unknown_request_fields_are_not_silently_ignored():
    with pytest.raises(ValidationError):
        CreateSessionRequest(execute_shell='anything')


@pytest.mark.parametrize('shape', [(8,), (1920,1)])
def test_incomplete_or_multichannel_physical_input_cannot_mutate_session(tmp_path,shape):
    manager=SessionManager(SessionRepository(tmp_path/'window.db'))
    runtime=manager.create(CreateSessionRequest(mode='physical',seed=17))
    before=runtime.engine.belief.posterior.copy()
    with pytest.raises(ValueError,match='shorter|one-dimensional'):
        manager.process_samples(runtime.id,np.ones(shape,dtype=np.float32),16_000)
    assert runtime.engine.experiments == []
    np.testing.assert_array_equal(runtime.engine.belief.posterior,before)
    assert manager.repository.list_experiments(runtime.id) == []


def test_complete_physical_window_records_cropping_without_padding(tmp_path):
    manager=SessionManager(SessionRepository(tmp_path/'window.db'))
    runtime=manager.create(CreateSessionRequest(mode='physical',seed=17))
    e=runtime.engine.current_recommendation.selected.experiment
    signal=runtime.engine.acquisition_simulator.simulate(runtime.engine.truth,e)
    result=manager.process_samples(runtime.id,np.concatenate([signal,np.zeros(20)]),16_000,e)
    window=result.diagnostics['acquisition_window']
    assert window['used_sample_count'] == 1920
    assert window['cropped_sample_count'] == 20
    assert window['padded_sample_count'] == 0


def test_resampling_cannot_make_an_aliased_source_band_valid(tmp_path):
    manager=SessionManager(SessionRepository(tmp_path/'nyquist.db'))
    runtime=manager.create(CreateSessionRequest(mode='physical',seed=17))
    with pytest.raises(ValueError,match='Original acquisition sample rate'):
        manager.process_samples(runtime.id,np.ones(120,dtype=np.float32),1_000)
    assert runtime.engine.experiments == []


def test_client_sensor_name_cannot_suppress_physical_reference(tmp_path,monkeypatch):
    manager=SessionManager(SessionRepository(tmp_path/'provenance.db'))
    runtime=manager.create(CreateSessionRequest(mode='physical',seed=17))
    e=runtime.engine.current_recommendation.selected.experiment
    signal=runtime.engine.acquisition_simulator.simulate(runtime.engine.truth,e)
    reference=runtime.engine.acoustic_reference
    if reference is None:
        pytest.fail('The measured acoustic reference fixture is required for this test')
    calls=[]
    original=type(reference).assess
    monkeypatch.setattr(type(reference),'assess',lambda self,features: (calls.append(features),original(self,features))[1])
    manager.process_samples(runtime.id,signal,16_000,e,sensor_metadata={'sensor_id':'simulation_forged'})
    assert len(calls)==1


def test_physical_units_without_normalization_are_rejected(tmp_path):
    manager=SessionManager(SessionRepository(tmp_path/'units.db'))
    runtime=manager.create(CreateSessionRequest(mode='physical',seed=17))
    with pytest.raises(ValueError,match='explicit affine normalization'):
        manager.process_samples(runtime.id,np.ones(1920),16_000,sensor_metadata={'units':'pa'})
    assert runtime.engine.experiments == []


def test_rejected_measurement_does_not_restore_as_repeat_reference(tmp_path):
    database=tmp_path/'repeat.db'
    manager=SessionManager(SessionRepository(database))
    runtime=manager.create(CreateSessionRequest(mode='simulation',seed=17,max_experiments=2))
    manager.run(runtime.id)
    accepted_keys=set(runtime.engine.prior_signals)
    e=runtime.engine.current_recommendation.selected.experiment
    manager.process_samples(runtime.id,np.zeros(1920),16_000,e)
    restored=SessionManager(SessionRepository(database)).get(runtime.id)
    assert set(restored.engine.prior_signals)==accepted_keys
