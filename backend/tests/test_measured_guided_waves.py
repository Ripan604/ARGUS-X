import itertools
from pathlib import Path
import h5py
import numpy as np
import pytest
from backend.app.evaluation.measured_guided_waves import (
    MeasuredPathOracle, ResponseModel, damage_index, fit_response_model,
    geometry_order, grid_points, kernel, read_native_bank, run_policy, summarize_weights,
)


def bank_fixture():
    t=np.arange(13108)/10000000
    base=np.broadcast_to(np.sin(2*np.pi*40000*t),(66,len(t))).copy()
    pairs=np.array(list(itertools.combinations(range(12),2)))
    return base,pairs,kernel(grid_points(),pairs)


def test_query_budget_is_not_an_unobserved_test_feature_budget():
    base,pairs,K=bank_fixture();test=base.copy();test[10]=np.roll(base[10],31)
    model=ResponseModel(.4,.1,10,.1)
    first=run_policy(MeasuredPathOracle(base,test,(.1,.2)),model,K,'adaptive_disagreement',budget=2)
    chosen=first['selected_indices']
    modified=test.copy()
    unused=np.setdiff1d(np.arange(66),chosen)
    modified[unused]=np.random.default_rng(1923).normal(size=(len(unused),13108))
    assert damage_index(base[unused[0]],modified[unused[0]])>.9
    second=run_policy(MeasuredPathOracle(base,modified,(.4,.4)),model,K,'adaptive_disagreement',budget=2)
    assert first['selected_indices']==second['selected_indices']
    assert first['trace'][0]['map_m']==second['trace'][0]['map_m']
    assert first['query_count']==2
    # Truth affects only post-execution scoring, never selected path or state.
    assert first['trace'][0]['damage_weight']==second['trace'][0]['damage_weight']


def test_oracle_truth_and_completed_lifecycle_are_sealed():
    base,_,_=bank_fixture();oracle=MeasuredPathOracle(base,base,(.1,.2))
    with pytest.raises(PermissionError):oracle.hidden_truth()
    oracle.query(0)
    with pytest.raises(ValueError,match='already'):oracle.query(0)
    assert oracle.end_evaluation()==(.1,.2)
    with pytest.raises(RuntimeError,match='completed'):oracle.query(1)


def test_rejected_path_still_consumes_an_opportunity():
    base,_,K=bank_fixture();test=base.copy();test[0]=0
    oracle=MeasuredPathOracle(base,test,None)
    result=run_policy(oracle,ResponseModel(.4,.1,10,.1),K,'cyclic',list(range(66)),budget=2)
    assert result['query_count']==2 and result['failed_opportunities']==1
    assert result['selected_indices']==[0,1]


def test_no_information_abstains_instead_of_detecting_prior_damage():
    base,_,K=bank_fixture()
    result=run_policy(MeasuredPathOracle(base,base,None),ResponseModel(0,.1,10,.1),K,'cyclic',list(range(66)),budget=1)
    assert result['trace'][0]['damage_decision'] is None
    assert result['trace'][0]['decision_abstained']


def test_conditional_map_is_stable_when_global_damage_mass_underflows():
    points=grid_points();logs=np.full(len(points),-10000.);logs[1374]=-9990.
    weights=np.r_[1.,np.zeros(len(points))]
    state=summarize_weights(weights,points,logs)
    assert state['map_m']==points[1374].tolist()
    assert state['damage_decision'] is False
    assert not state['location_supported_for_damage_decision']
    assert state['normalized_location_entropy']>0


@pytest.mark.parametrize('model',[ResponseModel(.4,0,1,0),ResponseModel(float('nan'),.1,1,.1),ResponseModel(2,.1,1,.1)])
def test_invalid_model_cannot_create_posterior_weights(model):
    base,_,K=bank_fixture()
    with pytest.raises(ValueError,match='model'):
        run_policy(MeasuredPathOracle(base,base,None),model,K,'cyclic',list(range(66)),budget=1)


def test_full_path_update_is_order_invariant():
    base,_,K=bank_fixture();test=base.copy();test[30]=np.roll(base[30],60)
    model=ResponseModel(.4,.1,10,.1)
    a=run_policy(MeasuredPathOracle(base,test,(.2,.3)),model,K,'cyclic',list(range(66)),budget=66)
    b=run_policy(MeasuredPathOracle(base,test,(.2,.3)),model,K,'cyclic',list(reversed(range(66))),budget=66)
    assert a['trace'][-1]['map_m']==b['trace'][-1]['map_m']
    assert a['trace'][-1]['damage_weight']==pytest.approx(b['trace'][-1]['damage_weight'])


def test_spatial_kernel_preserves_measured_geometry_and_training_fit():
    _,pairs,K=bank_fixture()
    points=np.array([[.065,.4],[.195,.33],[.335,.26]])
    train=.35*kernel(points,pairs).T
    model=fit_response_model(train,points,pairs)
    assert model.amplitude==pytest.approx(.35)
    assert model.noise_std==pytest.approx(.02)
    assert sorted(geometry_order(K,pairs))==list(range(66))


def test_one_coordinate_cannot_silently_broadcast_into_both_panel_axes():
    _,pairs,_=bank_fixture()
    with pytest.raises(ValueError,match='two-dimensional'):
        kernel(np.array([[.1],[.2]]),pairs)
    with pytest.raises(ValueError,match='within'):
        fit_response_model(np.full((3,66),-.1),np.array([[.1,.2],[.2,.3],[.3,.4]]),pairs)


def test_external_hdf5_link_is_rejected_before_following_it(tmp_path):
    path=tmp_path/'linked.h5'
    with h5py.File(path,'w') as h5:
        h5['pitchcatch']=h5py.ExternalLink('unavailable.h5','/')
    with pytest.raises(ValueError,match='hard-linked'):
        read_native_bank(path)


def test_native_record_is_not_relabeled_as_audio_range_data():
    path=Path('datasets/external/open_guided_waves/numeric/healthy/20181213T095826/pc_f40kHz.h5')
    if not path.exists():pytest.skip('Optional measured OGW data not downloaded')
    samples,pairs,metadata=read_native_bank(path)
    assert samples.shape==(66,13108) and len(pairs)==66
    assert metadata['sample_rate_hz']==10000000
    assert metadata['excitation_hz']==40000
    assert damage_index(samples[0],samples[0])==pytest.approx(0,abs=1e-12)
