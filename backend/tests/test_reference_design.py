from dataclasses import replace
import json

import numpy as np
import pytest

from backend.app.active_learning.reference_design import select_task_reference, reference_observation_std
from backend.app.core.config import ArgusConfig
from backend.app.control.dual_control import DualControlDecision
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Material, Panel, Experiment
from backend.app.services.engine import ArgusEngine


def setup():
    nuisance=NuisancePosterior.from_material(Material())
    panel=Panel()
    target=Experiment(.05,.1,.95,.9)
    references=[Experiment(.05,.08,x,.08,1200,3000,.28,.12,'chirp') for x in (.35,.65,.95)]
    return nuisance,panel,target,references


def design(nuisance,panel,target,refs,**kwargs):
    return select_task_reference(np.full((20,20),1/400),nuisance,panel,target,refs,
                                sample_rate=16000,cost_function=lambda _:0,**kwargs)


def test_all_posterior_mass_and_correlated_covariance_contribute():
    nuisance,panel,target,refs=setup()
    nuisance.velocity_timing_correlation=.65
    before=json.dumps(nuisance.to_dict(),sort_keys=True)
    result=design(nuisance,panel,target,refs)
    assert result.diagnostics['posterior_mass']==pytest.approx(1)
    assert result.diagnostics['cell_count']==400
    assert json.dumps(nuisance.to_dict(),sort_keys=True)==before
    for row in result.diagnostics['alternatives']:
        assert row['expected_task_variance_after_s2'] <= result.diagnostics['expected_task_variance_before_s2']
        delta=nuisance.propagation_covariance()-np.asarray(row['conditioned_covariance'])
        assert np.linalg.eigvalsh(delta).min()>=-1e-12


def test_candidate_order_cannot_change_unique_selection():
    nuisance,panel,target,refs=setup()
    first=design(nuisance,panel,target,refs)
    second=design(nuisance,panel,target,list(reversed(refs)))
    assert first.experiment==second.experiment
    assert first.diagnostics['selected']['objective_m2']==pytest.approx(min(
        row['objective_m2'] for row in first.diagnostics['alternatives']))


def test_cost_changes_selection_without_changing_metric_meaning():
    nuisance,panel,target,refs=setup()
    preferred=design(nuisance,panel,target,refs).experiment
    result=select_task_reference(np.ones((20,20)),nuisance,panel,target,refs,sample_rate=16000,
        cost_function=lambda e: 1e6 if e==preferred else 0)
    assert result.experiment!=preferred
    assert result.diagnostics['metric_scope'].endswith('not_location_error')


def test_different_paths_improve_reference_observability_without_forcing_it():
    nuisance,panel,target,refs=setup()
    std=reference_observation_std(nuisance,panel,16000)
    nuisance.update_direct_path(.18,.0008+.18/180,std,.75)
    result=design(nuisance,panel,target,refs)
    assert result.diagnostics['selected']['normalized_reference_design_rank']==2
    assert result.diagnostics['selected']['path_length_m']!=pytest.approx(.18)


@pytest.mark.parametrize('quality',[0,-1,float('nan'),2])
def test_invalid_assumed_quality_is_rejected(quality):
    nuisance,panel,target,refs=setup()
    with pytest.raises(ValueError): design(nuisance,panel,target,refs,assumed_quality=quality)


def test_engine_records_optional_reference_design_and_keeps_risk_route_separate(monkeypatch):
    engine=ArgusEngine(ArgusConfig(seed=17,enable_task_conditioned_calibration=True),seed=17)
    decision=DualControlDecision('calibration','Reference required',.8,.8,1,.1,.9,'wave_velocity',.4,'heuristic','direct_path')
    monkeypatch.setattr(engine.dual_control,'choose',lambda *a,**k:decision)
    before=engine.belief.posterior.copy()
    rec=engine._recommend()
    assert rec.action_type=='calibration'
    assert rec.structured_explanation['reference_design']['method']=='full_grid_task_conditioned_reference_v1'
    np.testing.assert_array_equal(before,engine.belief.posterior)
    assert engine.experiments==[]


def test_new_option_is_off_in_existing_default_configuration():
    assert ArgusConfig().enable_task_conditioned_calibration is False


def test_legacy_serial_contract_cannot_actuate_or_supply_localization_samples():
    from backend.app.hardware.devices import SerialProbeDevice
    device=SerialProbeDevice();device.connected=True
    class NoAcquisition:
        def write(self,*a): pytest.fail('Incompatible firmware was actuated')
    device._serial=NoAcquisition()
    with pytest.raises(RuntimeError,match='concurrent, trigger-referenced v2 frame'):
        device.acquire(Experiment(.05,.1,.95,.9),16000)


def test_final_study_keeps_acquisition_noise_identical_across_paired_policies():
    from pathlib import Path
    report=json.loads((Path(__file__).resolve().parents[2]/'research_results/final_task_calibration_2026_10_07.json').read_text())
    groups={}
    for row in report['runs']:
        groups.setdefault(row['seed'],[]).append(row)
    assert len(groups)==64
    for rows in groups.values():
        assert len(rows)==3
        assert all(row['completed'] for row in rows)
        for step in range(3):
            assert len({row['trace'][step]['acquisition_noise_std_s'] for row in rows})==1
            assert len({row['trace'][step]['shared_noise_s'] for row in rows})==1
