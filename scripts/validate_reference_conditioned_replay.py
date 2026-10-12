"""Development or separately acquired confirmation of reference-conditioned replay."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import re
from pathlib import Path
import sys
from time import perf_counter

import h5py
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.fit_healthy_reference_development import healthy_inputs,stream_sha
from backend.app.evaluation.healthy_wave_transport import (
    FitPolicy,HealthyWaveTransport,WarpFit,WarpParameters,transport_configuration,
)
from backend.app.evaluation.measured_guided_waves import (
    POSITIONS,damage_index,fit_response_model,geometry_order,grid_points,kernel,
    read_native_bank,summarize_weights,
)
from backend.app.evaluation.trajectory_reference_gate import (
    GateBinding,HealthyTrajectory,SelectedObservation,calibrate_reference_gate,evaluate_reference_prefix,
)
from backend.app.control.reference_conditioned import reference_control_disposition

CHECKPOINTS=(1,2,4,8,12,16)
VARIANTS=('raw_global','transport_global','transport_heteroscedastic')
POLICIES=('adaptive','geometry_spread','random')
SEED=20261008


def canonical(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def confirmation_receipt_ready(receipt):
    if not isinstance(receipt,dict) or receipt.get('completed') is not True:
        return False
    rows=receipt.get('files')
    if not isinstance(rows,list) or len(rows)!=29:
        raise ValueError('Completed confirmation receipt lacks 29 distinct declared banks')
    if (receipt.get('data_license')!='CC0' or receipt.get('selection_fixed_before_signal_analysis') is not True
            or receipt.get('native_sampling_frequency_hz')!=10000000
            or receipt.get('excitation_frequency_hz')!=40000 or receipt.get('recorded_unordered_paths')!=66
            or receipt.get('failures') or receipt.get('old_evidence_changed') is not False):
        raise ValueError('Completed confirmation receipt lacks the frozen provenance contract')
    expected={('healthy','healthy_trajectory_calibration',1,i,60-.5*(i-80),'cooling') for i in range(84,157,4)}
    expected|={('healthy','confirmation_test',2,i,t,'ascending') for i,t in ((181,30),(221,50))}
    expected|={(s,'confirmation_test',1,i,t,'ascending') for s in POSITIONS for i,t in ((20,30),(60,50))}
    observed=set();identities=set();hashes=set();paths=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Confirmation bank metadata must be an object')
        if (type(row.get('thermal_cycle')) is not int or type(row.get('index')) is not int
                or not isinstance(row.get('nominal_temperature_c'),(int,float))
                or isinstance(row.get('nominal_temperature_c'),bool)):
            raise ValueError('Confirmation condition identities require exact numeric types')
        key=tuple(row.get(k) for k in ('state','role','thermal_cycle','index','nominal_temperature_c','ramp'))
        if key not in expected or key in observed:raise ValueError('Confirmation roles/temperatures/cycles differ from the fixed 19 plus 10 plan')
        digest=row.get('sha256');identity=row.get('timestamp');path=row.get('local_path')
        if (not isinstance(digest,str) or re.fullmatch('[0-9a-f]{64}',digest) is None
                or not isinstance(identity,str) or re.fullmatch('[0-9]{8}T[0-9]{6}',identity) is None
                or not isinstance(path,str) or not path.startswith('datasets/external/open_guided_waves_confirmation/numeric/')
                or '\\' in path or '..' in Path(path).parts or ':' in path
                or digest in hashes or path in paths or (row['state'],identity) in identities
                or row.get('member_crc_verified') is not True or row.get('whole_archive_md5_verified') is not False):
            raise ValueError('Confirmation identities, path provenance or member verification is invalid')
        observed.add(key);identities.add((row['state'],identity));hashes.add(digest);paths.add(path)
    if observed!=expected:raise ValueError('Confirmation physical condition coverage is incomplete')
    original=json.loads((ROOT/'datasets/external/open_guided_waves/argus_manifest.json').read_text())
    if hashes & {row['sha256'] for row in original['files']}:
        raise ValueError('An original development capture was relabelled as confirmation')
    return True


def immutable(array):
    array=np.ascontiguousarray(array)
    return np.frombuffer(array.tobytes(),dtype=array.dtype).reshape(array.shape)


def load_fitted_transport():
    path=ROOT/'research_results/healthy_reference_development_2026_10_08.json'
    if path.stat().st_size>1024*1024:raise ValueError('Healthy fit report exceeds its metadata bound')
    report=json.loads(path.read_text())
    if report['metadata']['source_changed_during_run'] or report['metadata']['test_receiver_used']:
        raise ValueError('Healthy model was not fitted exclusively from stable development evidence')
    for name,digest in report['metadata']['source_sha256_after'].items():
        if stream_sha(ROOT/name)!=digest:raise ValueError('Healthy development source changed: '+name)
    c,p,T,rows,_=healthy_inputs();m=report['model'];policy=FitPolicy(**m['fit_policy'])
    training=sha256()
    for array in (c,p,T):training.update(np.ascontiguousarray(array,dtype='<f8').tobytes())
    implementation=stream_sha(ROOT/'backend/app/evaluation/healthy_wave_transport.py')
    if implementation!=m['implementation_source_sha256'] or training.hexdigest()!=m['training_sha256']:
        raise ValueError('Healthy model does not bind its actual source and anchors')
    identity={'training_sha256':m['training_sha256'],'implementation_source_sha256':implementation,
        'parameters':m['parameter_anchors'],'supported':m['supported_anchors'],'sigma':m['healthy_sigma'],
        'temperatures':m['temperature_means_c'],'sample_rate':10000000,'configuration':transport_configuration(policy)}
    if canonical(identity)!=m['model_sha256']:raise ValueError('Healthy model parameter identity mismatch')
    fits=tuple(tuple(WarpFit(**{**f,'parameters':WarpParameters(**f['parameters'])}) for f in anchor) for anchor in m['fits'])
    receiver=c[0]-c[0].mean(axis=1,keepdims=True);pitch=p[0]-p[0].mean(axis=1,keepdims=True)
    model=HealthyWaveTransport(immutable(np.asarray(m['temperature_means_c'])),immutable(receiver),immutable(pitch),
        immutable(np.asarray(m['parameter_anchors'])),immutable(np.asarray(m['supported_anchors'],dtype=bool)),
        immutable(np.asarray(m['healthy_sigma'])),immutable(np.asarray(m['development_damage_index'])),
        fits,m['training_sha256'],m['model_sha256'],policy,implementation)
    return model,rows


def load_rows(manifest_path):
    manifest=json.loads(manifest_path.read_text());banks=[]
    for row in manifest['files']:
        path=(ROOT/row['local_path']).resolve()
        if not path.is_relative_to((ROOT/'datasets/external').resolve()) or stream_sha(path)!=row['sha256']:
            raise ValueError('Native source identity or path mismatch')
        catch,pairs,meta=read_native_bank(path)
        if 'nominal_temperature_c' in row and abs(meta['chamber_temperature_c']-row['nominal_temperature_c'])>.25:
            raise ValueError('Actual measured confirmation condition differs from its role declaration')
        with h5py.File(path,'r') as h5:pitch=np.asarray(h5['pitchcatch/pitch'][()],dtype=float)
        banks.append({'catch':catch,'pitch':pitch,'pairs':pairs,'metadata':meta,'provenance':row})
    return manifest,banks


def direct_observation(variant,model,reference,bank,index):
    if variant=='raw_global':
        return damage_index(reference['catch'][index],bank['catch'][index]),.02,True,{}
    observation=model.observe(index,bank['metadata']['surface_temperature_c'],bank['pitch'][index],bank['catch'][index])
    return observation.damage_index,observation.healthy_sigma_path,observation.prediction.supported,observation.prediction.diagnostics()


class ConditionedOracle:
    def __init__(self,variant,model,reference,bank):
        self.variant,self._model,self._reference,self._bank=variant,model,reference,bank
        self.queries=[]
    def query(self,index):
        if index in self.queries:raise ValueError('Recorded path was already acquired')
        self.queries.append(index)
        try:
            di,sigma,accepted,diagnostics=direct_observation(self.variant,self._model,self._reference,self._bank,index)
            return SelectedObservation(index,di,sigma,accepted),diagnostics
        except ValueError as exc:
            # Rejected placeholder never enters likelihood or anomaly scoring.
            return SelectedObservation(index,0.,.02,False),{'supported':False,'rejection_reasons':[str(exc)]}


def replay(oracle,amplitude,sigma,K,eligible,policy,order,binding,calibration=None):
    means=np.column_stack((np.zeros(66),amplitude*K));weights=np.r_[.5,np.full(2500,.5/2500)]
    logs=np.log(weights);observations=[];traces=[];started=perf_counter()
    for step in range(CHECKPOINTS[-1]):
        if policy=='adaptive':
            expectation=means@weights
            score=np.maximum(0,(means*means)@weights-expectation*expectation)/(sigma*sigma)
            score[~eligible]=-np.inf;score[oracle.queries]=-np.inf;index=int(np.argmax(score))
        else:index=int(order[step])
        row,diagnostics=oracle.query(index);observations.append(row)
        if row.accepted:
            logs+=-.5*((row.corrected_damage_index-means[index])/sigma[index])**2
            logs-=logs.max();weights=np.exp(logs);weights/=weights.sum()
        state=summarize_weights(weights,grid_points(),logs[1:])
        trace={'budget':step+1,'path_index':index,'accepted':row.accepted,
               'damage_index':row.corrected_damage_index if row.accepted else None,
               'healthy_sigma':row.healthy_sigma,'reference_diagnostics':diagnostics,**state}
        if step+1 in CHECKPOINTS:
            numerical_reference_qualification=bool(np.isfinite(amplitude) and 0<=amplitude<=1
                                                   and np.isfinite(sigma[eligible]).all() and np.all(sigma[eligible]>=.02))
            decision=evaluate_reference_prefix(calibration,tuple(observations),binding,
                block_id=oracle._bank['provenance']['timestamp'],source_sha256=oracle._bank['provenance']['sha256'],
                reference_qualified=all(o.accepted for o in observations),model_quality_accepted=numerical_reference_qualification)
            disposition=reference_control_disposition(decision,binding,remaining_budget=16-step-1,current_experiment_index=step+1)
            trace['reference_gate']=decision.to_dict();trace['control_disposition']=disposition.to_dict()
            trace['qualification_scope']='numerical_controller_and_healthy_reference_checks_only'
            trace['structural_localization_model_validated']=False
        traces.append(trace)
    alerts=[row['budget'] for row in traces if row.get('reference_gate',{}).get('status')=='supported_anomaly']
    return {'queries':oracle.queries,'observations':tuple(observations),'trace':traces,'elapsed_ms':(perf_counter()-started)*1000,
            'any_prefix_supported_anomaly':bool(alerts),'earliest_supported_anomaly_budget':min(alerts) if alerts else None,
            'control_requests_are_recorded_not_physically_executed':True,
            'failed_opportunities':sum(not x.accepted for x in observations)}


def run_study(stage):
    old=ROOT/'datasets/external/open_guided_waves/argus_manifest.json'
    confirmation=ROOT/'datasets/external/open_guided_waves_confirmation/argus_manifest.json'
    receipt=json.loads(confirmation.read_text()) if confirmation.exists() else {'completed':False,'files':[]}
    if stage=='confirmation' and not confirmation_receipt_ready(receipt):
        return {'status':'blocked_missing_confirmation_acquisitions','stage':stage,'confirmation_scored':False,
            'acquired_new_banks':len(receipt.get('files',[])),'required_new_banks':29,
            'required_healthy_calibration_blocks':19,'reason':'original_public_source_returned_HTTP_403',
            'gate_field_coverage_established':False,'synthetic_replacements_used':False}
    paths=[Path(__file__),ROOT/'backend/app/evaluation/healthy_wave_transport.py',
        ROOT/'backend/app/evaluation/trajectory_reference_gate.py',ROOT/'backend/app/control/reference_conditioned.py',
        ROOT/'docs/REFERENCE_CONDITIONED_CONFIRMATION_PROTOCOL.md',
        ROOT/'research_results/healthy_reference_development_2026_10_08.json',old,
        *sorted((ROOT/'datasets/external/open_guided_waves/numeric').rglob('*.h5'))]
    if stage=='confirmation':paths.extend([confirmation,*sorted((confirmation.parent/'numeric').rglob('*.h5'))])
    before={p.relative_to(ROOT).as_posix():stream_sha(p) for p in paths}
    started=perf_counter();transport,healthy_rows=load_fitted_transport();manifest,banks=load_rows(old)
    pairs=banks[0]['pairs'];K=kernel(grid_points(),pairs)
    eligible=np.all(transport.supported_anchors,axis=0)
    if eligible.sum()<16:raise ValueError('Healthy-qualified paths cannot support the frozen horizon')
    indices=np.flatnonzero(eligible);spread=[x for x in geometry_order(K,pairs) if eligible[x]]
    references={round(b['metadata']['chamber_temperature_c']):b for b in banks
                if b['provenance']['state']=='healthy' and b['provenance']['thermal_cycle']==1}
    rng=np.random.default_rng(SEED);orders=[rng.permutation(indices).tolist() for _ in range(16)]
    if stage=='confirmation':
        _,new_banks=load_rows(confirmation)
        calibration_banks=[b for b in new_banks if b['provenance']['role']=='healthy_trajectory_calibration']
        test_banks=[b for b in new_banks if b['provenance']['role']=='confirmation_test']
    else:
        calibration_banks=[b for b in banks if b['provenance']['state']=='healthy' and b['provenance']['thermal_cycle']==2]
        test_banks=calibration_banks+[b for b in banks if b['provenance']['state'] in POSITIONS]
    runs=[];models=[];calibrations=[];failures=[]
    for variant in VARIANTS:
        for held_out in POSITIONS:
            training=[b for b in banks if b['provenance']['state'] in POSITIONS and b['provenance']['state']!=held_out]
            values=[];locations=[]
            try:
                for bank in training:
                    nominal=round(bank['metadata']['chamber_temperature_c']);reference=references[min(references,key=lambda t:abs(t-nominal))]
                    obs=[direct_observation(variant,transport,reference,bank,int(i)) for i in indices]
                    if not all(o[2] for o in obs):raise ValueError('Development source/reference acquisition unsupported')
                    values.append([o[0] for o in obs]);locations.append(POSITIONS[bank['provenance']['state']])
                values=np.asarray(values);locations=np.asarray(locations)
                response=fit_response_model(values,locations,pairs[indices])
                sigma=np.full(66,response.noise_std)
                if variant=='transport_heteroscedastic':
                    residual=values-response.amplitude*kernel(locations,pairs[indices]).T
                    sigma[indices]=np.sqrt(np.mean(residual*residual,axis=0)+transport.healthy_sigma[indices]**2)
                model_record={'variant':variant,'held_out_position':held_out,'amplitude':response.amplitude,
                    'sigma':sigma.tolist(),'eligible_indices':indices.tolist(),'transport_model_sha256':transport.model_sha256,
                    'training_bank_sha256':[b['provenance']['sha256'] for b in training]}
                model_sha=canonical(model_record);models.append({**model_record,'model_sha256':model_sha})
            except ValueError as exc:
                failures.append({'variant':variant,'held_out_position':held_out,'phase':'training','error':str(exc)})
                continue
            for policy in POLICIES:
                policy_orders=orders if policy=='random' else [spread if policy=='geometry_spread' else None]
                for order_index,order in enumerate(policy_orders):
                    binding=GateBinding(model_sha,canonical({'policy':policy,'order':order,'eligible':indices.tolist(),
                        'horizon':16,'implementation_sha256':stream_sha(Path(__file__))}),
                        stream_sha(ROOT/'docs/REFERENCE_CONDITIONED_CONFIRMATION_PROTOCOL.md'),
                        canonical([r['sha256'] for r in healthy_rows]),budgets=CHECKPOINTS)
                    trajectories=[];calibration=None;cal_error=None
                    for bank in calibration_banks:
                        nominal=round(bank['metadata']['chamber_temperature_c']);reference=references[min(references,key=lambda t:abs(t-nominal))]
                        trial=replay(ConditionedOracle(variant,transport,reference,bank),response.amplitude,sigma,K,eligible,policy,order,binding)
                        trajectories.append(HealthyTrajectory(bank['provenance']['timestamp'],bank['provenance']['sha256'],
                            trial['observations'],binding,complete=trial['failed_opportunities']==0))
                    try:calibration=calibrate_reference_gate(trajectories,binding)
                    except ValueError as exc:cal_error=str(exc)
                    calibrations.append({'variant':variant,'held_out_position':held_out,'policy':policy,'order_index':order_index,
                        'source_role':'new_cooling_confirmation_calibration' if stage=='confirmation' else 'previously_seen_healthy_cycle2_development_calibration',
                        'calibration':calibration.to_dict() if calibration else None,'error':cal_error})
                    selected=[b for b in test_banks if b['provenance']['state'] in ('healthy',held_out)]
                    for bank in selected:
                        nominal=round(bank['metadata']['chamber_temperature_c']);reference=references[min(references,key=lambda t:abs(t-nominal))]
                        trial=replay(ConditionedOracle(variant,transport,reference,bank),response.amplitude,sigma,K,eligible,policy,order,binding,calibration)
                        trial.pop('observations')
                        state=bank['provenance']['state']
                        # Labels enter only after the entire acquisition trajectory.
                        for row in trial['trace']:
                            row['conditional_location_error_mm']=float(np.linalg.norm(np.asarray(row['map_m'])-POSITIONS[state])*1000) if state in POSITIONS else None
                        runs.append({'variant':variant,'policy':policy,'held_out_position':held_out,'order_index':order_index,
                            'test_state':state,'temperature_c':bank['metadata']['chamber_temperature_c'],
                            'source_sha256':bank['provenance']['sha256'],**trial})
    summary=[]
    for variant in VARIANTS:
        for policy in POLICIES:
            subset=[r for r in runs if r['variant']==variant and r['policy']==policy]
            groups={}
            for r in subset:groups.setdefault((r['held_out_position'],r['test_state'],round(r['temperature_c'])),[]).append(r)
            damage=[];healthy=[]
            for key,group in groups.items():
                final=[r['trace'][-1] for r in group]
                if key[1]=='healthy':healthy.append(np.mean([r['damage_decision'] is True for r in final]))
                else:damage.append(np.mean([r['conditional_location_error_mm'] for r in final]))
            summary.append({'variant':variant,'policy':policy,'damage_conditions':len(damage),
                'mean_conditional_location_error_mm':float(np.mean(damage)) if damage else None,
                'descriptive_healthy_model_positive_rate':float(np.mean(healthy)) if healthy else None,
                'gate_supported_anomaly_count':sum(r['trace'][-1]['reference_gate']['status']=='supported_anomaly' for r in subset),
                'gate_any_prefix_supported_anomaly_count':sum(r['any_prefix_supported_anomaly'] for r in subset),
                'gate_unsupported_count':sum(r['trace'][-1]['reference_gate']['status']=='unsupported' for r in subset),
                'trajectories':len(subset)})
    after={p.relative_to(ROOT).as_posix():stream_sha(p) for p in paths}
    return {'status':'completed' if not failures else 'partial_with_retained_failures','stage':stage,
        'confirmation_scored':stage=='confirmation','metadata':{'evidence_source':'measured_reference_conditioned_'+stage,
        'previously_seen_data':stage=='development','independent_specimens':1,'healthy_qualified_paths':int(eligible.sum()),
        'budgets':list(CHECKPOINTS),'model_variants':list(VARIANTS),'random_orders':16,
        'source_sha256_before':before,'source_sha256_after':after,'source_changed_during_run':before!=after,
        'elapsed_s':perf_counter()-started,'healthy_sigma_is_residual_proxy':True,
        'gate_exchangeability_verified':False,'gate_field_coverage_established':False,
        'development_healthy_banks_reused_as_calibration_not_unseen_test':stage=='development'},
        'models':models,'calibrations':calibrations,'failures':failures,'summary':summary,'runs':runs}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=('development','confirmation'),default='development')
    args=parser.parse_args();output=ROOT/f'research_results/reference_conditioned_{args.stage}_2026_10_08.json'
    if output.exists():raise SystemExit('Preserve existing experimental evidence')
    with threadpool_limits(limits=1):result=run_study(args.stage)
    output.write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'status':result['status'],'summary':result.get('summary')},indent=2))
