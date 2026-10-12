"""Paired synthetic reference-selection study; records failures and source hashes."""
from pathlib import Path
from hashlib import sha256
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.active_learning.reference_design import select_task_reference,reference_observation_std
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Material,Panel,Experiment,physical_distance

paths=[Path(__file__),*sorted((ROOT/'backend/app').rglob('*.py'))]
hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes()).hexdigest() for p in paths}
panel=Panel();target=Experiment(.05,.1,.95,.9)
refs=[Experiment(.05,.08,x,.08,1200,3000,.28,.12,'chirp') for x in (.35,.65,.95)]
posterior=np.full((20,20),1/400)
y,x=np.indices(posterior.shape);x=(x+.5)/20;y=(y+.5)/20
target_paths=(physical_distance(target.source_x,target.source_y,x,y,panel)
              +physical_distance(x,y,target.receiver_x,target.receiver_y,panel))
runs=[]
for seed in range(83000,83064):
    rng=np.random.default_rng(seed)
    true_velocity=float(np.clip(rng.normal(180,28),85,395))
    true_timing=float(np.clip(rng.normal(.0008,.00022),.00005,.0039))
    innovations=rng.normal(size=3)
    acquisition_nuisance=NuisancePosterior.from_material(Material(wave_velocity=true_velocity))
    acquisition_std=reference_observation_std(acquisition_nuisance,panel,16000)/np.sqrt(.75)
    for policy in ('repeated_short_reference','cyclic_first_feasible','task_conditioned'):
        nuisance=NuisancePosterior.from_material(Material());trace=[]
        try:
            for step in range(3):
                selection=select_task_reference(posterior,nuisance,panel,target,refs,sample_rate=16000,cost_function=lambda _:0)
                e=(refs[0] if policy=='repeated_short_reference' else refs[step % len(refs)]
                   if policy=='cyclic_first_feasible' else selection.experiment)
                d=float(physical_distance(e.source_x,e.source_y,e.receiver_x,e.receiver_y,panel))
                std=reference_observation_std(nuisance,panel,16000)
                observed=true_timing+d/true_velocity+float(innovations[step])*acquisition_std
                if observed<=0: raise ValueError('Synthetic reference fell outside positive-delay support')
                nuisance.update_direct_path(d,observed,std,.75)
                trace.append({'step':step+1,'path_m':d,'observed_delay_s':observed,
                              'acquisition_noise_std_s':acquisition_std,
                              'shared_noise_s':float(innovations[step])*acquisition_std,
                              'assumed_reference_std_s':std,
                              'propagation_covariance':nuisance.propagation_covariance().tolist()})
            predicted=nuisance.parameter('timing_offset').mean+target_paths/nuisance.parameter('wave_velocity').mean
            truth=true_timing+target_paths/true_velocity
            rmse_us=float(np.sqrt(np.sum(posterior*(predicted-truth)**2))*1e6)
            modeled=float(np.sum(posterior*nuisance.arrival_variance(target_paths)))
            runs.append({'seed':seed,'policy':policy,'completed':True,'target_arrival_rmse_us':rmse_us,
                         'velocity_absolute_error_m_s':abs(nuisance.parameter('wave_velocity').mean-true_velocity),
                         'timing_absolute_error_us':abs(nuisance.parameter('timing_offset').mean-true_timing)*1e6,
                         'modeled_target_variance_s2':modeled,'trace':trace})
        except (ValueError,RuntimeError) as exc:
            runs.append({'seed':seed,'policy':policy,'completed':False,'error':str(exc),'trace':trace})
summary={}
for policy in ('repeated_short_reference','cyclic_first_feasible','task_conditioned'):
    complete=[r for r in runs if r['policy']==policy and r['completed']]
    summary[policy]={'attempted':64,'completed':len(complete),'failures':64-len(complete)}
    for key in ('target_arrival_rmse_us','velocity_absolute_error_m_s','timing_absolute_error_us','modeled_target_variance_s2'):
        summary[policy]['mean_'+key]=float(np.mean([r[key] for r in complete])) if complete else None
lookup={(r['seed'],r['policy']):r for r in runs}
paired=[]
for seed in range(83000,83064):
    a,b=lookup[seed,'cyclic_first_feasible'],lookup[seed,'task_conditioned']
    if a['completed'] and b['completed']: paired.append(a['target_arrival_rmse_us']-b['target_arrival_rmse_us'])
boot=np.random.default_rng(91071)
interval=np.percentile(np.asarray(paired)[boot.integers(len(paired),size=(10000,len(paired)))].mean(1),[2.5,97.5]).tolist() if paired else None
report={'metadata':{'evidence_source':'synthetic_scalar_arrival_only','seeds':list(range(83000,83064)),
    'reference_steps':3,'source_sha256':hashes,'source_changed_during_run':any(sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in hashes.items()),
    'metric':'grid_target_arrival_prediction_not_defect_localization','assumed_quality':.75,
    'acquisition_noise':'fixed by sealed true velocity and declared pose/timing noise; common innovations across policies',
    'limitations':['local Gaussian calibration','fixed geometry and uniform posterior','no hardware measurements','cost disabled in efficacy comparison']},
    'summary':summary,'paired':{'comparison':'task_conditioned_vs_cyclic_first_feasible','complete_pairs':len(paired),'mean_advantage_us':float(np.mean(paired)) if paired else None,'bootstrap_95ci_us':interval},'runs':runs}
out=ROOT/'research_results/final_task_calibration_2026_10_07.json'
out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'summary':summary,'paired':report['paired'],'source_stable':not report['metadata']['source_changed_during_run']},indent=2))
