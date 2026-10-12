"""Create source-checked measured-data Markdown and scientific figures."""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
FILES={'gfrp':'measured_gfrp_validation_2026_10_08.json',
       'impact':'measured_impact_validation_2026_10_08.json',
       'ogw':'measured_guided_wave_validation_2026_10_08.json',
       'morpho':'measured_morpho_quality_2026_10_08.json'}
reports={k:json.loads((ROOT/'research_results'/name).read_text()) for k,name in FILES.items()}
for key,report in reports.items():
    before=report.get('input_source_sha256_before',report.get('metadata',{}).get('source_sha256_before'))
    after=report.get('input_source_sha256_after',report.get('metadata',{}).get('source_sha256_after'))
    if before!=after or after is None:raise RuntimeError('Study source changed or absent: '+key)
    for name,digest in after.items():
        path=ROOT/name;hasher=sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):hasher.update(chunk)
        if hasher.hexdigest()!=digest:raise RuntimeError('Evidence source changed: '+name)
gfrp,impact,ogw,morpho=(reports[k] for k in ('gfrp','impact','ogw','morpho'))
if not ogw['completed'] or ogw['bank_failures'] or ogw['fold_failures']:
    raise RuntimeError('Measured path comparison did not complete')
folder=ROOT/'output/figures';folder.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                    'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white'})
colors=['#718697','#087f8c','#d18734']
models=gfrp['evaluation']['models']
keys=['majority_no_features','logistic_regression','random_forest']
fig,ax=plt.subplots(figsize=(8.3,3.8))
for i,key in enumerate(keys):
    mean=models[key]['aggregate']['balanced_accuracy']*100
    lo,hi=np.array(models[key]['plate_cluster_bootstrap']['ci95_percentile']['balanced_accuracy'])*100
    ax.bar(i,mean,color=colors[i],width=.55,yerr=[[mean-lo],[hi-mean]],capsize=6)
    ax.text(i,hi+2,f'{mean:.1f}%',ha='center',fontweight='bold')
ax.set_xticks(range(3),['Majority baseline','Logistic regression','Random forest'])
ax.set_ylim(0,103);ax.set_ylabel('Balanced accuracy (%)')
ax.set_title('Measured GFRP tap screening: whole plates held out')
ax.axhline(50,color='#718697',ls=':',lw=1)
fig.text(.5,.01,'2,568 recordings / 8 plate clusters; bootstrap intervals condition on fitted out-of-fold predictions.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(folder/'measured_gfrp_scores.png',dpi=220);plt.close(fig)

labels={'cyclic':'Cyclic','geometry_spread':'Geometry spread','training_static':'Training static',
        'random':'Random (16 orders)','adaptive_disagreement':'Adaptive disagreement'}
palette={'cyclic':'#d18734','geometry_spread':'#906ca0','training_static':'#679557',
         'random':'#718697','adaptive_disagreement':'#087f8c'}
fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
for ax,context,title in zip(axes,('condition_matched_baseline','twenty_degree_baseline'),('Condition-matched baseline','20 C baseline at every temperature')):
    for policy,label in labels.items():
        rows=[r for r in ogw['summary'] if r['context']==context and r['policy']==policy]
        ax.plot([r['budget'] for r in rows],[r['mean_location_error_mm'] for r in rows],marker='o',ms=3,color=palette[policy],label=label)
    for policy,marker,label in [('full_bank_model','s','Full model / 66 paths'),('full_bank_RAPID','^','RAPID / 66 paths')]:
        values=[r['trace'][-1]['location_error_mm'] if policy=='full_bank_model' else r['location_error_mm']
                for r in ogw['full_bank_references'] if r['context']==context and r['policy']==policy and r['test_state']!='healthy']
        ax.scatter([66],[np.mean(values)],marker=marker,color='#243847',s=48,label=label)
    ax.set_title(title,fontsize=10);ax.set_xlabel('Recorded paths revealed');ax.set_xticks([1,8,16,32,66]);ax.grid(alpha=.15)
axes[0].set_ylabel('Mean conditional MAP error (mm)')
handles,legend=axes[0].get_legend_handles_labels()
fig.legend(handles,legend,loc='lower center',ncol=4,fontsize=8)
fig.suptitle('OGW measured-path replay: 4 reference positions on one plate',fontsize=12,fontweight='bold')
fig.tight_layout(rect=(0,.14,1,.92));fig.savefig(folder/'measured_ogw_budget.png',dpi=220);plt.close(fig)

fig,ax=plt.subplots(figsize=(8.3,3.8))
names=['train_centroid','knn_1','knn_3','calibrated_tdoa_q05']
means=[impact['summary'][k]['mean_error_mm'] for k in names]
ax.bar(range(4),means,color=['#718697','#aaadb0','#d18734','#087f8c'],width=.6)
for i,key in enumerate(names):
    errors=[f['errors_mm'][key] for f in impact['folds']]
    ax.scatter(np.full(len(errors),i)+np.linspace(-.12,.12,len(errors)),errors,color='#243847',s=13,alpha=.7)
    ax.text(i,means[i]+6,f'{means[i]:.1f} mm',ha='center',fontsize=9)
ax.set_xticks(range(4),['Train centroid','1 neighbour','3 neighbours','Calibrated TDoA'])
ax.set_ylabel('Source-position error (mm)');ax.set_title('Bologna measured source localization / 9 position holdouts')
fig.text(.5,.01,'Bars: mean; dots: retained position errors. One plate, previously seen data; no specimen-generalization interval.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(folder/'measured_impact_errors.png',dpi=220);plt.close(fig)

fig,ax=plt.subplots(figsize=(8.3,3.6))
names=['logistic_regression','random_forest','majority_dummy']
caught=[morpho['summary'][k]['pooled_completed_fold_metrics']['true_bad'] for k in names]
missed=[136-n for n in caught]
ax.barh(range(3),caught,color='#087f8c',label='BAD correctly flagged')
ax.barh(range(3),missed,left=caught,color='#cb857e',label='BAD missed')
for i,(c,m) in enumerate(zip(caught,missed)):ax.text(c+max(2,m*.25),i,f'{m}/136 BAD missed',va='center',fontsize=9)
ax.set_yticks(range(3),['Logistic regression','Random forest','Majority baseline']);ax.invert_yaxis()
ax.set_xlim(0,136);ax.set_xlabel('Actively selected operator-labelled BAD signals')
ax.set_title('MORPHO panel holdouts: quality rejection failed at threshold 0.5')
handles,legend=ax.get_legend_handles_labels()
fig.legend(handles,legend,loc='lower center',bbox_to_anchor=(.5,.01),ncol=2,fontsize=9,frameon=False)
fig.tight_layout(rect=(0,.17,1,1));fig.savefig(folder/'measured_morpho_bad_recall.png',dpi=220);plt.close(fig)

suite=ET.parse(ROOT/'output/release/measured-data-backend-tests.xml').getroot().find('testsuite')
if int(suite.attrib['failures']) or int(suite.attrib['errors']):raise RuntimeError('Verification failed')
passed=int(suite.attrib['tests'])-int(suite.attrib['skipped'])
lines=['# ARGUS measured-data campaign and results',
    '**Prepared:** 8 October 2026. Public measured-data evaluations, preserved with complete source and raw-data provenance.',
    '## What has now been achieved',
    'Two new measured datasets were acquired: 18 complete Open Guided Waves banks (250.18 MB) and the MORPHO curated dataset (97.89 MB). '
    'The existing GFRP and Bologna recordings were also audited and reanalysed. No downloaded code or pickle model was executed. '
    'Public lab measurements were used directly at their documented sampling rates; missing paths, labels and reciprocal responses were not synthesized.',
    'The strongest positive finding is plate-held-out audio-tap screening. Measured source localization also improves over a train-centroid baseline. '
    'The native ultrasonic path study exposes substantial location errors and healthy false positives. The cross-panel signal-quality classifier fails at its frozen threshold. '
    'These four outcomes describe different tasks and cannot be combined into one inspection-accuracy percentage.',
    '## Sources, licenses and actual independent units',
    '| Dataset | Measured subset and task | Independent units / license |',
    '|---|---|---|',
    '| [TU Darmstadt GFRP](https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b) | 2,568 microphone taps, 51.2 kHz; pointwise intact/defect screening | Eight plates; CC BY 4.0 |',
    '| [Bologna AE](https://zenodo.org/records/10875042) | Nine 2 MHz, three-sensor position records; transient source localization | One plate / nine positions; CC BY 4.0 |',
    '| [Open Guided Waves 2](https://doi.org/10.6084/m9.figshare.c.4488089.v1) | 18 native 10 MHz banks / 40 kHz excitation / 66 actual paths | One plate / four removable mass positions; CC0 |',
    '| [MORPHO](https://zenodo.org/records/20120070) | 12,504 native 1 MHz signals; 1,011 selected GOOD/BAD labels | Five panels; labels actively selected; CC BY 4.0 |',
    'OGW whole archives exceed 160 GB; bounded ZIP64 byte ranges retrieved only the selected full HDF5 banks. '
    'Each selected member has checked CRC32 and local SHA-256. The publisher whole-archive MD5 remains explicitly unverified. '
    'MORPHO files and the existing GFRP/Bologna source files were checked against published checksums. Exact URLs, actual temperatures, coordinates, schemas and licenses remain in acquisition manifests.',
    '## GFRP: a positive measured screening result',
    'Four folds held out whole plates; all channels, points and repeats from a test plate stayed out of training. '
    'Features were recomputed from raw WAVs, filename/coordinate labels were excluded, scaling was fitted on training data, and all out-of-fold predictions were retained.',
    '| Model | Balanced accuracy | ROC-AUC | F1 | Overall accuracy |',
    '|---|---|---|---|---|']
for key,label in zip(keys,['Majority baseline','Logistic regression','Random forest']):
    m=models[key]['aggregate'];lines.append(f"| {label} | {m['balanced_accuracy']:.3f} | {m['roc_auc']:.3f} | {m['f1']:.3f} | {m['accuracy']:.3f} |")
lines += ['Logistic regression balanced accuracy is 83.8%, with a plate-cluster percentile interval of 75.2-91.5%. '
    'Its confusion counts are 396 detected defect-labelled taps, 72 missed taps, 1,743 correctly intact-labelled taps and 357 false defect-labelled taps. '
    'RF has higher overall accuracy but worse balanced accuracy, AUC and F1. Class imbalance makes the majority baseline 81.8% accurate despite detecting no defect-labelled taps.',
    'The interval uses only eight plate clusters and conditions on fitted predictions; models are not refitted inside the bootstrap. '
    'Ten within-plate label permutation controls were near chance. This supports pointwise screening within this acquisition domain, not location, defect type, adaptive measurement efficiency or the user apparatus.',
    '## Bologna: measured source localization with strict position holdouts',
    'Each complete position was held out. A bounded inverse-speed/two-relative-offset TDoA calibration used the other eight positions. '
    'The complete 1 m plate was searched on a fixed 5 mm grid. Three-neighbour preprocessing also used training data only. No numerical simulation data entered this reanalysis.',
    '| Method | Mean error (mm) | Median (mm) | Within 100 mm |',
    '|---|---|---|---|']
for key,label in zip(['train_centroid','knn_1','knn_3','calibrated_tdoa_q05'],['Train centroid','One neighbour','Three neighbours','Calibrated TDoA']):
    m=impact['summary'][key];lines.append(f"| {label} | {m['mean_error_mm']:.2f} | {m['median_error_mm']:.2f} | {100*m['success_within_100_mm']:.1f}% |")
lines += ['The 108.99 mm mean TDoA error is about 39.8% below the train-centroid error, but no held-out event is within 20 mm. '
    'This is a previously seen record on one plate, not new unseen validation or a persistent hidden-defect test. '
    'The CSV schema is 5,000 by three with columns s1/s2/s3; a separately identified repetition axis is absent even though the provider description mentions repeated experiments.',
    '## OGW: first native measured-path replay result',
    'A new offline evaluation branch preserves 40 kHz/10 MHz observations instead of converting them into audio-range data. '
    'A fixed RAPID-style elliptical response model was calibrated on three reference positions; every temperature of the fourth position stayed held out. '
    'The second healthy thermal cycle was never used for calibration. Five policies revealed only the requested test path, with the same inference and path budgets.',
    'The 960 trajectories include random-order repetitions and repeated trained models. They are not 960 independent physical trials: only four reference positions, twelve damage-condition banks and three unique healthy test banks support evaluation.',
    '| 32-path policy | Matched mean conditional error (mm) | 20 C baseline mean error (mm) | Matched conditional success within 50 mm |',
    '|---|---|---|---|']
for policy,label in labels.items():
    matched=next(r for r in ogw['summary'] if r['policy']==policy and r['budget']==32 and r['context']=='condition_matched_baseline')
    shifted=next(r for r in ogw['summary'] if r['policy']==policy and r['budget']==32 and r['context']=='twenty_degree_baseline')
    lines.append(f"| {label} | {matched['mean_location_error_mm']:.2f} | {shifted['mean_location_error_mm']:.2f} | {100*matched['success_50_mm']:.1f}% |")
lines += ['Adaptive matched-baseline conditional MAP error is 160.76 mm versus random 190.70 mm. '
    'However, its model calls only 50% of the reference-scatterer conditions damaged and falsely flags 66.7% of healthy condition/model evaluations. '
    'Those evaluations reuse three healthy test banks under four trained models. Conditional distance success is not joint operational detection/localization success.',
    'The full 66-path model has matched-baseline mean error 213.28 mm; classical full-bank RAPID has 209.43 mm. '
    'The full banks cost 66 reveals and are not equal-budget competitors. More evidence can worsen error when an observation model is misspecified. '
    'With a 20 C baseline at all test temperatures, adaptive mean error is 200.04 mm and there are no conditional 50 mm successes at 32 paths.',
    'All trajectories completed with zero rejected opportunities. Modeled containment can be broad despite its apparent coverage; it is not a calibrated confidence region. '
    'The fixed global kernel/noise model and cross-date temperature/coupling differences remain major limitations. '
    'No beta, window or threshold was retuned on held-out results. A successful first run was preserved as a preflight pilot; the final rerun changed only validation/exception handling and meaningful causality tests. Every location metric remained identical.',
    '## MORPHO: a negative cross-panel quality result',
    'Five complete panels were held out in turn. GOOD/BAD are actively selected human signal-quality labels, not defect labels. '
    'One panel has no BAD-labelled examples, so that fold has undefined AUC/balanced accuracy; it remains in the recorded evaluation. '
    'Actual HDF5 cycle counts disagree with the README, and the schema audit retains both.',
    '| Model | Balanced accuracy | BAD found / 136 | BAD recall |',
    '|---|---|---|---|']
for key,label in zip(['logistic_regression','random_forest','majority_dummy'],['Logistic regression','Random forest','Majority baseline']):
    m=morpho['summary'][key]['pooled_completed_fold_metrics'];lines.append(f"| {label} | {m['balanced_accuracy']:.3f} | {m['true_bad']} / 136 | {100*m['bad_recall']:.2f}% |")
lines += ['RF misses 135 of 136 BAD signals at the frozen 0.5 threshold. Its 0.772 ranking AUC and 85.95% overall accuracy do not make it a working rejection gate. '
    'The majority baseline is 86.55% accurate while rejecting none of the BAD signals. Strong panel prevalence differences and selected labels limit interpretation. '
    'No threshold was retuned and no quality classifier was deployed.',
    '## What the project now contains',
    'The repository contains reproducible public-data acquisition, native HDF5 validation, a causally restricted path oracle, whole-group evaluation, simple baselines, complete failures/negative findings, and source/raw hashes. '
    'The new replay module is for offline research and is separate from physical session execution. The operating apparatus still needs its own measured timing/transfer bench and blind physical inspection.',
    f'The full measured release verification passed {passed} tests with one deliberate legacy-pickle skip. '
    'No physical probe was flashed or actuated for this campaign. Licenses and attribution remain with each source. Data acquisition alone does not establish patent novelty.',
    '## Reproduction',
    '```powershell',
    '.venv\\Scripts\\python.exe scripts\\download_open_guided_waves.py',
    '.venv\\Scripts\\python.exe scripts\\download_morpho_dataset.py',
    '.venv\\Scripts\\python.exe scripts\\validate_measured_gfrp.py',
    '.venv\\Scripts\\python.exe scripts\\validate_measured_impact.py',
    '.venv\\Scripts\\python.exe scripts\\validate_measured_guided_waves.py',
    '.venv\\Scripts\\python.exe scripts\\validate_measured_morpho_quality.py',
    '.venv\\Scripts\\python.exe scripts\\export_measured_web_summary.py',
    '```',
    'Preserve final reports. The impact/OGW commands refuse overwriting existing evidence; choose a new dated output when intentionally repeating them. '
    'The other commands should likewise be run with a new output path when retaining an earlier result. Dependency pins include h5py 3.16.0. '
    'All full study reports and protocols are under research_results/ and docs/. The Research page shows a compact task-separated summary.',
    '## Source-bound result artifacts',
    '| Study | Result file | SHA-256 |','|---|---|---|']
for key,name in FILES.items():lines.append(f"| {key.upper()} | research_results/{name} | {sha256((ROOT/'research_results'/name).read_bytes()).hexdigest()} |")
formatted=[];inside_code=False;previous=''
for line in lines:
    separator='\n' if inside_code or (line.startswith('|') and previous.startswith('|')) else '\n\n'
    formatted.append((separator if formatted else '')+line)
    if line.startswith('```'):inside_code=not inside_code
    previous=line
(ROOT/'docs/MEASURED_RESULTS_2026_10_08.md').write_text(''.join(formatted)+'\n',encoding='utf-8')
print('Created measured-data report and four scientific figures; all input hashes current.')
