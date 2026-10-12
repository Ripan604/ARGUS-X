"""Experimental acquisition disposition after whole-trajectory reference checks.

This produces reviewable requests, not actuator commands or structural releases.
The native-wave experiment remains separate from the production probe adapter.
"""
from dataclasses import asdict, dataclass
import math
import re
from typing import Literal

from backend.app.evaluation.trajectory_reference_gate import GateBinding, GateDecision


@dataclass(frozen=True)
class VerificationReceipt:
    accepted: bool
    diverse_path: bool
    source_contract_checked: bool
    model_sha256: str
    reference_sha256: str
    experiment_index: int

    def __post_init__(self):
        if any(type(getattr(self,key)) is not bool for key in ('accepted','diverse_path','source_contract_checked')):
            raise ValueError('Verification flags require exact Boolean attestations')
        if (type(self.experiment_index) is not int or not 1<=self.experiment_index<=66
                or any(not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None
                       for value in (self.model_sha256,self.reference_sha256))):
            raise ValueError('Verification requires a bounded index and exact source bindings')


@dataclass(frozen=True)
class ReferenceControlDisposition:
    action: Literal['REQUEST_QUALIFIED_REFERENCE','REQUEST_DIVERSE_VERIFICATION',
                    'CONTINUE_DIAGNOSTIC','STOP_BUDGET_UNRESOLVED','REVIEW_VERIFIED_ANOMALY']
    reason: str
    gate_status: str
    next_physical_action_authorized: bool = False
    operator_review_required: bool = True
    healthy_release_supported: bool = False
    defect_location_certified: bool = False

    def to_dict(self):return asdict(self)


def reference_control_disposition(decision:GateDecision,binding:GateBinding,*,
                                  remaining_budget:int,current_experiment_index:int,
                                  verification:VerificationReceipt|None=None) -> ReferenceControlDisposition:
    if not isinstance(decision,GateDecision) or not isinstance(binding,GateBinding):
        raise ValueError('A bound experimental gate decision is required')
    if (type(remaining_budget) is not int or not 0<=remaining_budget<=66
            or type(current_experiment_index) is not int or not 1<=current_experiment_index<=66):
        raise ValueError('Recorded-path budget and current index must be explicit and bounded')
    if verification is not None and not isinstance(verification,VerificationReceipt):
        raise ValueError('Verification requires a typed, bound receipt')
    if decision.status=='unsupported':
        return ReferenceControlDisposition('REQUEST_QUALIFIED_REFERENCE',decision.reason,decision.status)
    valid_probability=lambda value: (isinstance(value,(int,float)) and not isinstance(value,bool)
                                     and math.isfinite(value) and 0<value<=1)
    coherent=bool(decision.binding_sha256==binding.binding_sha256()
        and type(decision.calibration_count) is int and decision.calibration_count>=19
        and valid_probability(decision.minimum_p_value) and valid_probability(decision.reference_p_value)
        and abs(decision.minimum_p_value-1/(decision.calibration_count+1))<1e-12
        and decision.minimum_p_value<=.05 and decision.budget in binding.budgets
        and not decision.field_coverage_claimed and not decision.localization_supported
        and ((decision.status=='supported_anomaly' and decision.reference_p_value<=.05)
             or (decision.status=='background_consistent' and decision.reference_p_value>.05)))
    if not coherent:
        return ReferenceControlDisposition('REQUEST_QUALIFIED_REFERENCE','gate_identity_or_rank_evidence_invalid',decision.status)
    if decision.status=='supported_anomaly':
        fresh=bool(verification is not None and verification.accepted and verification.diverse_path
                   and verification.source_contract_checked
                   and verification.experiment_index==current_experiment_index
                   and verification.experiment_index>decision.budget
                   and verification.model_sha256==binding.model_sha256
                   and verification.reference_sha256==binding.reference_sha256)
        if fresh:
            return ReferenceControlDisposition('REVIEW_VERIFIED_ANOMALY','fresh_bound_diverse_verification',decision.status)
        if remaining_budget:
            return ReferenceControlDisposition('REQUEST_DIVERSE_VERIFICATION','anomaly_requires_independent_verification',decision.status)
        return ReferenceControlDisposition('STOP_BUDGET_UNRESOLVED','anomaly_unverified_budget_exhausted',decision.status)
    if decision.status=='background_consistent':
        return ReferenceControlDisposition('CONTINUE_DIAGNOSTIC' if remaining_budget else 'STOP_BUDGET_UNRESOLVED',
                                           'reference_consistency_is_not_a_healthy_release',decision.status)
    raise ValueError('Unsupported experimental gate status')
