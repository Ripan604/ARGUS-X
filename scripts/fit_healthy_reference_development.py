"""Fit only existing healthy development anchors; no test receiver is opened."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

import h5py
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.evaluation.healthy_wave_transport import fit_healthy_transport
from backend.app.evaluation.measured_guided_waves import read_native_bank


def stream_sha(path:Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>64*1024*1024:
        raise ValueError('Development file missing, linked or oversized')
    digest=sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def healthy_inputs():
    manifest_path=ROOT/'datasets/external/open_guided_waves/argus_manifest.json'
    manifest=json.loads(manifest_path.read_text())
    rows=sorted([r for r in manifest['files'] if r['state']=='healthy' and r['thermal_cycle']==1],
                key=lambda r:r['chamber_temperature_c'])
    if len(rows)!=3 or manifest['failures']:
        raise ValueError('Exactly the three original healthy first-cycle warming anchors are required')
    catches=[];pitches=[];surfaces=[]
    for row in rows:
        path=(ROOT/row['local_path']).resolve()
        if not path.is_relative_to((ROOT/'datasets/external/open_guided_waves').resolve()):
            raise ValueError('Healthy source path escaped the original data directory')
        if stream_sha(path)!=row['sha256']:raise ValueError('Original healthy waveform checksum changed')
        catch,pairs,meta=read_native_bank(path)
        with h5py.File(path,'r') as handle:
            # The native reader has already validated this internal dataset's
            # schema and bounded storage before any source array is loaded.
            pitch=np.asarray(handle['pitchcatch/pitch'][()],dtype=float)
        catches.append(catch);pitches.append(pitch);surfaces.append(meta['surface_temperature_c'])
    return np.asarray(catches),np.asarray(pitches),np.asarray(surfaces),rows,manifest_path


def fit_development():
    catch,pitch,T,rows,manifest=healthy_inputs()
    paths=[Path(__file__),ROOT/'backend/app/evaluation/healthy_wave_transport.py',
           ROOT/'backend/tests/test_healthy_wave_transport.py',ROOT/'docs/HEALTHY_WAVE_TRANSPORT_PROTOCOL.md',
           ROOT/'docs/REFERENCE_CONDITIONED_CONFIRMATION_PROTOCOL.md',manifest,
           *[ROOT/r['local_path'] for r in rows]]
    before={p.relative_to(ROOT).as_posix():stream_sha(p) for p in paths}
    started=perf_counter()
    model=fit_healthy_transport(catch,pitch,T)
    after={p.relative_to(ROOT).as_posix():stream_sha(p) for p in paths}
    qualified=np.all(model.supported_anchors,axis=0)
    report={'metadata':{'evidence_source':'measured_healthy_metrology_development_only',
        'input_role':'healthy_first_cycle_warming_only','test_receiver_used':False,
        'confirmation_performed':False,'independent_specimens':1,'healthy_anchors':3,
        'source_sha256_before':before,'source_sha256_after':after,'source_changed_during_run':before!=after,
        'elapsed_s':perf_counter()-started},'source_banks':rows,'model':model.to_dict(),
        'summary':{'recorded_paths':66,'qualified_path_count':int(qualified.sum()),
            'supported_anchor_counts':np.sum(model.supported_anchors,axis=1).tolist(),
            'mean_healthy_middle_left_out_DI':float(model.development_damage_index.mean()),
            'median_healthy_middle_left_out_DI':float(np.median(model.development_damage_index)),
            'max_healthy_middle_left_out_DI':float(model.development_damage_index.max()),
            'residual_scale_is_a_proxy':True,'field_accuracy_established':False}}
    return model,report


if __name__=='__main__':
    output=ROOT/'research_results/healthy_reference_development_2026_10_08.json'
    if output.exists():raise SystemExit('Development fit evidence already exists; preserve it')
    with threadpool_limits(limits=1):model,report=fit_development()
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'summary':report['summary'],
        'source_changed':report['metadata']['source_changed_during_run']},indent=2))
