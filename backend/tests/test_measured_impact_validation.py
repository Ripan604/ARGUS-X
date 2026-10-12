import numpy as np
import pytest
from scripts.validate_measured_impact import evaluate_fold, localize_tdoa, SENSORS, train_tdoa


def fixture():
    positions=np.array([[.2,.2],[.8,.2],[.2,.8],[.8,.8],[.5,.5]])
    distances=np.linalg.norm(positions[:,None,:]-SENSORS[None,:,:],axis=2)
    times=distances/2200+np.array([0.,.00001,-.00002])
    features=np.zeros((5,3,12)); features[:,:,1]=times
    features[:,:,6]=np.arange(5)[:,None]+1
    return features,positions


def test_exact_training_tdoa_geometry_recovers_sensor_offsets():
    features,positions=fixture()
    calibration=train_tdoa(features[:,:,1],positions)
    assert calibration['effective_speed_m_s']==pytest.approx(2200,rel=1e-5)
    np.testing.assert_allclose(calibration['relative_sensor_offsets_s'],[.00001,-.00002],atol=1e-9)
    for times,position in zip(features[:,:,1],positions):
        np.testing.assert_allclose(localize_tdoa(times,calibration),position,atol=.005)


def test_held_out_values_cannot_enter_scaler_or_timing_calibration():
    features,positions=fixture()
    original=evaluate_fold(features,positions,4)
    changed=features.copy();changed[4,:,6]=1e8;changed[4,:,1]=.0009
    alternative=evaluate_fold(changed,positions,4)
    assert alternative['train_scaler_means']==original['train_scaler_means']
    assert alternative['tdoa_calibration']==original['tdoa_calibration']
    assert 4 not in original['train_indices']


def test_identical_source_position_cannot_be_split_between_train_and_test():
    features,positions=fixture();positions[3]=positions[4]
    with pytest.raises(ValueError,match='leaked'):
        evaluate_fold(features,positions,4)


def test_measured_csvs_remain_published_checksum_bound():
    from scripts.validate_measured_impact import load_measured
    features,positions,provenance=load_measured()
    assert features.shape==(9,3,12) and positions.shape==(9,2)
    assert all(p['published_md5_verified'] for p in provenance)
    assert len(set(tuple(p) for p in positions))==9
