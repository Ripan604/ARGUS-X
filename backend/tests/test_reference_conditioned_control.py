from dataclasses import replace
import pytest
from backend.app.control.reference_conditioned import VerificationReceipt, reference_control_disposition
from backend.app.evaluation.trajectory_reference_gate import GateBinding,GateDecision


def fixtures(status):
    binding=GateBinding('a'*64,'b'*64,'c'*64,'d'*64)
    decision=GateDecision(status,'fixture',12,1,.5 if status=='background_consistent' else .05,19,.05,
                          binding_sha256=binding.binding_sha256())
    return decision,binding


def test_unsupported_reference_requests_recalibration_even_with_no_budget():
    decision,binding=fixtures('unsupported')
    result=reference_control_disposition(decision,binding,remaining_budget=0,current_experiment_index=16)
    assert result.action=='REQUEST_QUALIFIED_REFERENCE'
    assert not result.next_physical_action_authorized


@pytest.mark.parametrize('budget',[0,16])
def test_background_consistency_never_releases_a_healthy_structure(budget):
    decision,binding=fixtures('background_consistent')
    result=reference_control_disposition(decision,binding,remaining_budget=budget,current_experiment_index=16)
    assert not result.healthy_release_supported and not result.defect_location_certified


def test_unverified_anomaly_cannot_survive_budget_as_verified():
    decision,binding=fixtures('supported_anomaly')
    result=reference_control_disposition(decision,binding,remaining_budget=0,current_experiment_index=16)
    assert result.action=='STOP_BUDGET_UNRESOLVED'


@pytest.mark.parametrize('mutation',[{'experiment_index':15},{'model_sha256':'e'*64},
    {'reference_sha256':'e'*64},{'diverse_path':False},{'source_contract_checked':False}])
def test_stale_reciprocal_or_unbound_verification_does_not_finish_inspection(mutation):
    decision,binding=fixtures('supported_anomaly')
    receipt=VerificationReceipt(True,True,True,binding.model_sha256,binding.reference_sha256,16)
    result=reference_control_disposition(decision,binding,remaining_budget=16,current_experiment_index=16,
                                          verification=replace(receipt,**mutation))
    assert result.action=='REQUEST_DIVERSE_VERIFICATION'


def test_fresh_verified_anomaly_is_sent_for_review_without_auto_actuation():
    decision,binding=fixtures('supported_anomaly')
    receipt=VerificationReceipt(True,True,True,binding.model_sha256,binding.reference_sha256,16)
    result=reference_control_disposition(decision,binding,remaining_budget=0,current_experiment_index=16,verification=receipt)
    assert result.action=='REVIEW_VERIFIED_ANOMALY'
    assert result.operator_review_required and not result.next_physical_action_authorized


def test_verification_cannot_reuse_the_anomaly_measurement():
    decision,binding=fixtures('supported_anomaly')
    receipt=VerificationReceipt(True,True,True,binding.model_sha256,binding.reference_sha256,12)
    result=reference_control_disposition(decision,binding,remaining_budget=4,current_experiment_index=12,verification=receipt)
    assert result.action=='REQUEST_DIVERSE_VERIFICATION'


@pytest.mark.parametrize('mutation',[{'binding_sha256':'e'*64},{'reference_p_value':.99},
    {'minimum_p_value':.001},{'calibration_count':3},{'reference_p_value':float('nan')}])
def test_inconsistent_or_mismatched_rank_cannot_produce_an_anomaly_review(mutation):
    decision,binding=fixtures('supported_anomaly')
    result=reference_control_disposition(replace(decision,**mutation),binding,remaining_budget=4,current_experiment_index=16)
    assert result.action=='REQUEST_QUALIFIED_REFERENCE'


def test_untyped_verification_is_an_explicit_input_error():
    decision,binding=fixtures('supported_anomaly')
    with pytest.raises(ValueError,match='typed'):
        reference_control_disposition(decision,binding,remaining_budget=4,current_experiment_index=16,verification='claimed')
