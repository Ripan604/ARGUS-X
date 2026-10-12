"""Frozen native-frequency, position-held-out measured OGW path replay."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import zlib

import h5py
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.evaluation.measured_guided_waves import (
    BUDGETS, MeasuredPathOracle, POSITIONS, SENSORS, damage_index, fit_response_model,
    geometry_order, grid_points, kernel, rapid_full_bank, read_native_bank, run_policy,
)

SOURCE=ROOT/'datasets/external/open_guided_waves'
TEMPERATURES=(20,40,60)
CONTEXTS=('condition_matched_baseline','twenty_degree_baseline')
POLICIES=('cyclic','geometry_spread','training_static','adaptive_disagreement','random')
RANDOM_ORDERS=16
SEED=20261008


def fingerprints() -> dict:
    paths=[Path(__file__),ROOT/'backend/app/evaluation/measured_guided_waves.py',
           ROOT/'backend/tests/test_measured_guided_waves.py',ROOT/'docs/MEASURED_GUIDED_WAVE_PROTOCOL.md',
           ROOT/'scripts/download_open_guided_waves.py',SOURCE/'argus_manifest.json',
           SOURCE/'metadata/geometry.json',SOURCE/'metadata/primary_article.xml',
           *sorted((SOURCE/'metadata').glob('figshare_*.json')),*sorted((SOURCE/'numeric').rglob('*.h5'))]
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths}


def load_sources() -> tuple[dict,np.ndarray,list[dict],list[dict]]:
    manifest=json.loads((SOURCE/'argus_manifest.json').read_text())
    if manifest['data_license']!='CC0' or manifest['failures'] or len(manifest['files'])!=18:
        raise ValueError('A complete licensed 18-bank acquisition manifest is required')
    geometry=json.loads((SOURCE/'metadata/geometry.json').read_text())
    if not np.array_equal(np.asarray(geometry['sensor_coordinates_m']),SENSORS) or geometry['reference_damage_coordinates_m']!={k:list(v) for k,v in POSITIONS.items()}:
        raise ValueError('Frozen geometry differs from the independently published coordinates')
    banks={};records=[];failures=[];pairs=None
    for row in manifest['files']:
        try:
            path=(ROOT/row['local_path']).resolve()
            if not path.is_relative_to(SOURCE.resolve()):raise ValueError('Measurement path escapes data directory')
            content=path.read_bytes()
            if (len(content)!=row['member_size'] or sha256(content).hexdigest()!=row['sha256']
                    or f'{zlib.crc32(content)&0xffffffff:08x}'!=row['member_crc32']):
                raise ValueError('Raw member checksum, SHA256 or size failed')
            values,current_pairs,meta=read_native_bank(path)
            if pairs is not None and not np.array_equal(pairs,current_pairs):raise ValueError('Recorded path bank changed')
            if meta['source_zero_energy_paths']:raise ValueError('Source drive missing on a recorded path')
            pairs=current_pairs
            temperature=min(TEMPERATURES,key=lambda t:abs(t-meta['chamber_temperature_c']))
            if abs(temperature-meta['chamber_temperature_c'])>.25:raise ValueError('Selected chamber setpoint differs from frozen protocol')
            key=(row['state'],int(row['thermal_cycle']),temperature)
            if key in banks:raise ValueError('Duplicate condition/cycle in source subset')
            banks[key]=values
            records.append({'bank_key':list(key),'file':row['local_path'],'sha256':row['sha256'],
                'source_archive_url':row['archive_url'],'member_crc32_verified':True,
                'whole_archive_md5_verified':False,**meta})
        except (ValueError,OSError,KeyError,TypeError) as exc:
            failures.append({'file':row.get('local_path'),'error':str(exc)})
    expected={('healthy',cycle,t) for cycle in (1,2) for t in TEMPERATURES}|{(state,1,t) for state in POSITIONS for t in TEMPERATURES}
    if set(banks)!=expected:failures.append({'error':'Complete physical condition coverage unavailable'})
    return banks,pairs,records,failures


def development_data(banks:dict,pairs:np.ndarray,held_out:str,context:str):
    responses=[];locations=[];keys=[]
    for state,position in POSITIONS.items():
        if state==held_out:continue
        for temperature in TEMPERATURES:
            reference_temperature=temperature if context=='condition_matched_baseline' else 20
            reference=banks[('healthy',1,reference_temperature)]
            trial=banks[(state,1,temperature)]
            responses.append([damage_index(reference[p],trial[p]) for p in range(len(pairs))])
            locations.append(position);keys.append([state,1,temperature])
    return np.asarray(responses),np.asarray(locations),keys


def aggregate(runs:list[dict]) -> list[dict]:
    rows=[]
    # Random-order repetitions are first collapsed within a physical condition
    # and trained model, never counted as independently acquired test banks.
    for context in CONTEXTS:
        for policy in POLICIES:
            subset=[r for r in runs if r['context']==context and r['policy']==policy]
            for budget in BUDGETS:
                case_groups={}
                for run in subset:
                    if len(run['trace'])<budget:continue
                    key=(run['held_out_position'],run['test_state'],run['nominal_temperature_c'])
                    case_groups.setdefault(key,[]).append(run['trace'][budget-1])
                damage=[];healthy=[];per_position={}
                for key,traces in case_groups.items():
                    item={'held_out_position':key[0],'test_state':key[1],'nominal_temperature_c':key[2],
                          'policy_order_repetitions':len(traces),
                          'mean_damage_weight':float(np.mean([t['damage_weight'] for t in traces])),
                          'damage_decision_rate':float(np.mean([t['damage_decision'] is True for t in traces])),
                          'abstention_rate':float(np.mean([t['decision_abstained'] for t in traces]))}
                    if key[1]!='healthy':
                        errors=np.asarray([t['location_error_mm'] for t in traces])
                        item.update({'mean_location_error_mm':float(errors.mean()),
                            'median_location_error_mm':float(np.median(errors)),
                            'conditional_region_coverage':float(np.mean([t['conditional_region_covers_truth'] for t in traces])),
                            **{f'success_{radius}_mm':float(np.mean(errors<=radius)) for radius in (25,50,100)}})
                        damage.append(item);per_position.setdefault(key[0],[]).append(item)
                    else:healthy.append(item)
                rows.append({'context':context,'policy':policy,'budget':budget,
                    'damage_condition_count':len(damage),'independent_damage_positions':len(per_position),
                    'unique_healthy_test_banks':3,'healthy_condition_model_evaluations':len(healthy),
                    'mean_location_error_mm':float(np.mean([x['mean_location_error_mm'] for x in damage])),
                    'mean_damage_decision_rate':float(np.mean([x['damage_decision_rate'] for x in damage])),
                    'mean_healthy_false_positive_condition_model_rate':float(np.mean([x['damage_decision_rate'] for x in healthy])),
                    'mean_healthy_abstention_rate':float(np.mean([x['abstention_rate'] for x in healthy])),
                    'mean_conditional_region_coverage':float(np.mean([x['conditional_region_coverage'] for x in damage])),
                    **{f'success_{radius}_mm':float(np.mean([x[f'success_{radius}_mm'] for x in damage])) for radius in (25,50,100)},
                    'per_position_mean_error_mm':{k:float(np.mean([x['mean_location_error_mm'] for x in v])) for k,v in per_position.items()},
                    'conditions':damage+healthy})
    return rows


def run_study() -> dict:
    before=fingerprints();started=perf_counter()
    banks,pairs,records,bank_failures=load_sources()
    base={'metadata':{'evidence_source':'measured_ultrasonic_offline_path_replay','protocol':'docs/MEASURED_GUIDED_WAVE_PROTOCOL.md',
        'doi':'10.6084/m9.figshare.c.4488089.v1','data_license':'CC0','source_sha256_before':before,
        'independent_specimens':1,'independent_reference_damage_positions':4,'unique_damage_test_banks':12,
        'unique_healthy_test_banks':3,'healthy_model_evaluations_repeat_those_three_banks':True,
        'native_sample_rate_hz':10000000,'excitation_hz':40000,'recorded_paths':66,
        'budgets':list(BUDGETS),'random_orders_per_case':RANDOM_ORDERS,'seed':SEED,
        'numerical_thread_limit':1,'h5py_version':h5py.__version__,'numpy_version':np.__version__,
        'limitations':['one_plate_four_surface_mass_surrogates','offline_reveal_budget_not_online_acquisition',
            'path_independence_and_elliptical_Gaussian_response_are_approximations','weights_not_field_calibrated',
            'condition_matching_is_not_unseen_temperature_generalization','native_ultrasound_not_audio_range_probe',
            'all66_references_cost_more_than_sparse32_policies','no_specimen_generalization_interval',
            'whole_archive_md5_unverified_partial_members_CRC_SHA_verified','standard_RAPID_Bayes_principles_not_claimed_novel']},
        'source_banks':records,'bank_failures':bank_failures,'models':[],'runs':[],'full_bank_references':[]}
    if bank_failures:
        base['completed']=False
    else:
        K=kernel(grid_points(),pairs);spread=geometry_order(K,pairs)
        rng=np.random.default_rng(SEED)
        random_orders=[rng.permutation(66).tolist() for _ in range(RANDOM_ORDERS)]
        for context in CONTEXTS:
            for held_out in POSITIONS:
                development,locations,training_keys=development_data(banks,pairs,held_out,context)
                model=fit_response_model(development,locations,pairs)
                static=np.argsort(-np.var(development,axis=0),kind='stable').tolist()
                base['models'].append({'context':context,'held_out_position':held_out,
                    'training_bank_keys':training_keys,'training_DI':development.tolist(),
                    'training_positions_m':locations.tolist(),'training_static_order':static,**model.to_dict()})
                for state in (held_out,'healthy'):
                    for temperature in TEMPERATURES:
                        reference_temperature=temperature if context=='condition_matched_baseline' else 20
                        reference=banks[('healthy',1,reference_temperature)]
                        test=banks[(state,2 if state=='healthy' else 1,temperature)]
                        truth=POSITIONS[state] if state!='healthy' else None
                        identity={'context':context,'held_out_position':held_out,'test_state':state,
                                  'nominal_temperature_c':temperature,'reference_nominal_temperature_c':reference_temperature}
                        for policy in POLICIES:
                            orders=random_orders if policy=='random' else [None if policy=='adaptive_disagreement' else
                                spread if policy=='geometry_spread' else static if policy=='training_static' else list(range(66))]
                            for order_index,order in enumerate(orders):
                                result=run_policy(MeasuredPathOracle(reference,test,truth),model,K,policy,order)
                                base['runs'].append({**identity,'random_order_index':order_index if policy=='random' else None,**result})
                        full=run_policy(MeasuredPathOracle(reference,test,truth),model,K,'full_bank_model',list(range(66)),budget=66)
                        rapid=rapid_full_bank(MeasuredPathOracle(reference,test,truth),K)
                        base['full_bank_references'].append({**identity,**full})
                        base['full_bank_references'].append({**identity,**rapid})
        base['summary']=aggregate(base['runs']);base['completed']=True
    after=fingerprints()
    base['metadata'].update({'source_sha256_after':after,'source_changed_during_run':before!=after,
        'elapsed_s':perf_counter()-started,'trajectory_count':len(base['runs']),
        'failed_opportunities':sum(r['failed_opportunities'] for r in base['runs'])})
    return base


if __name__=='__main__':
    output=ROOT/'research_results/measured_guided_wave_validation_2026_10_08.json'
    if output.exists():raise SystemExit('Final measured evidence exists; preserve it instead of overwriting')
    with threadpool_limits(limits=1):result=run_study()
    output.write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'completed':result['completed'],
        'source_changed':result['metadata']['source_changed_during_run'],
        'failed_opportunities':result['metadata']['failed_opportunities'],
        'budget32':[r for r in result.get('summary',[]) if r['budget']==32]},indent=2))
