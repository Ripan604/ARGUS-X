"""Native ultrasonic measured-path replay, separate from the audio-range engine.

The elliptical response model and posterior-disagreement selector are explicit
offline approximations. No future test-path waveform or truth enters selection.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import itertools
import json
from pathlib import Path
from time import perf_counter

import h5py
import numpy as np

MAX_HDF5_BYTES = 64 * 1024 * 1024
GRID_SIZE = 50
BETA = 1.05
NOISE_FLOOR = .02
BUDGETS = (1,2,4,8,12,16,32)
SENSORS = np.array([[x,y] for y in (.470,.030) for x in (.450,.370,.290,.210,.130,.050)])
POSITIONS = {"D04":(.065,.400),"D12":(.195,.330),"D16":(.335,.260),"D24":(.450,.190)}


def grid_points() -> np.ndarray:
    axis = (np.arange(GRID_SIZE)+.5) * .5/GRID_SIZE
    y,x = np.meshgrid(axis,axis,indexing="ij")
    return np.column_stack((x.ravel(),y.ravel()))


def read_native_bank(path: Path) -> tuple[np.ndarray,np.ndarray,dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_HDF5_BYTES:
        raise ValueError("HDF5 file missing, linked or oversized")
    with h5py.File(path,"r") as h5:
        def numeric(name, shape):
            node = h5
            for part in name.split("/"):
                if not isinstance(node.get(part,getlink=True),h5py.HardLink):
                    raise ValueError("Only internal hard-linked numeric HDF5 paths are supported")
                node = node[part]
            if (not isinstance(node,h5py.Dataset) or node.shape != shape
                    or node.dtype.kind not in "iuf" or node.dtype.itemsize > 8
                    or node.is_virtual or node.external
                    or node.size*node.dtype.itemsize > MAX_HDF5_BYTES):
                raise ValueError("HDF5 numeric schema or storage is unsupported")
            if node.chunks and int(np.prod(node.chunks))*node.dtype.itemsize > MAX_HDF5_BYTES:
                raise ValueError("HDF5 chunk exceeds the bounded allocation")
            properties=node.id.get_create_plist()
            for index in range(properties.get_nfilters()):
                filter_id=properties.get_filter(index)[0]
                if filter_id not in {1,2,3,4,5,6} or not h5py.h5z.filter_avail(filter_id):
                    raise ValueError("Unsupported HDF5 filter/plugin")
            values = node[()]
            if not np.isfinite(values).all():
                raise ValueError("HDF5 contains nonfinite observations")
            return values
        samples=numeric("pitchcatch/catch",(66,13108)).astype(float)
        pitch=numeric("pitchcatch/pitch",(66,13108))
        raw_pairs=numeric("command/pitchcatch/channels",(66,2))
        if raw_pairs.dtype.kind not in "iu":
            raise ValueError("Recorded channel identifiers require exact integer storage")
        pairs=raw_pairs.astype(int)
        expected=np.array(list(itertools.combinations(range(12),2)))
        if not np.array_equal(pairs,expected):
            raise ValueError("Recorded channel order/coverage differs from the 66 actual paths")
        rate=numeric("command/pitchcatch/sampling_frequency",(1,)).item()
        frequency=numeric("command/pitchcatch/signal_frequency",(1,)).item()
        cycles=numeric("command/pitchcatch/signal_cycles",(1,)).item()
        if rate != 10000000 or frequency != 40000 or cycles != 5:
            raise ValueError("Native excitation/clock contract differs from the frozen study")
        meta={"sample_rate_hz":rate,"excitation_hz":frequency,"cycles":cycles,
              "sample_count":samples.shape[1],"path_count":len(pairs),
              "chamber_temperature_c":numeric("CTC/Temperature",(1,)).item(),
              "surface_temperature_c":numeric("Temperature/values",(2,)).tolist(),
              "source_zero_energy_paths":np.flatnonzero(np.std(pitch,axis=1)<1e-12).tolist()}
    return samples,pairs,meta


def damage_index(reference: np.ndarray, observation: np.ndarray) -> float:
    if reference.shape != observation.shape or reference.ndim != 1:
        raise ValueError("Reference/test waveforms must share a complete native window")
    a=reference.astype(float)-reference.mean();b=observation.astype(float)-observation.mean()
    denominator=float(np.linalg.norm(a)*np.linalg.norm(b))
    if not np.isfinite(denominator) or denominator < 1e-12:
        raise ValueError("Zero-energy or invalid reference/test path")
    return float(np.clip(1-abs(float(np.dot(a,b)/denominator)),0,1))


def kernel(points: np.ndarray, pairs: np.ndarray) -> np.ndarray:
    points=np.asarray(points);pairs=np.asarray(pairs)
    if (points.ndim!=2 or points.shape[1]!=2 or not np.isfinite(points).all()
            or np.any(points<0) or np.any(points>.5) or pairs.ndim!=2 or pairs.shape[1]!=2
            or pairs.dtype.kind not in 'iu' or np.any(pairs<0) or np.any(pairs>=12)
            or np.any(pairs[:,0]==pairs[:,1])):
        raise ValueError("Spatial geometry requires bounded two-dimensional points and actual channel pairs")
    start,end=SENSORS[pairs[:,0]],SENSORS[pairs[:,1]]
    direct=np.linalg.norm(start-end,axis=1)
    lengths=np.linalg.norm(points[None,:,:]-start[:,None,:],axis=2)+np.linalg.norm(points[None,:,:]-end[:,None,:],axis=2)
    return np.maximum(0,(BETA-lengths/direct[:,None])/(BETA-1))


@dataclass(frozen=True)
class ResponseModel:
    amplitude: float
    noise_std: float
    training_rows: int
    training_residual_rmse: float

    def to_dict(self):
        return self.__dict__.copy()


def fit_response_model(train_di: np.ndarray, train_positions: np.ndarray,
                       pairs: np.ndarray) -> ResponseModel:
    if train_di.shape != (len(train_positions),len(pairs)) or not np.isfinite(train_di).all():
        raise ValueError("Development response/label shape is invalid")
    if np.any(train_di<0) or np.any(train_di>1):
        raise ValueError("Damage-index observations must be within [0,1]")
    K=kernel(train_positions,pairs).T
    denominator=float(np.sum(K*K))
    if denominator <= 1e-12:
        raise ValueError("Training reference locations provide no modeled path support")
    amplitude=float(np.clip(np.sum(K*train_di)/denominator,0,1))
    residual=float(np.sqrt(np.mean((train_di-amplitude*K)**2)))
    return ResponseModel(amplitude,max(NOISE_FLOOR,residual),train_di.size,residual)


class MeasuredPathOracle:
    """Only queried path observations are exposed during a policy trajectory."""
    def __init__(self,reference:np.ndarray,test:np.ndarray,truth:tuple[float,float]|None):
        if reference.shape != test.shape or reference.shape != (66,13108):
            raise ValueError("Complete 66-path native response bank required")
        self._reference,self._test,self._truth=reference,test,truth
        self.queries=[]
        self._ended=False

    def query(self,index:int) -> float:
        if self._ended:
            raise RuntimeError("A completed evaluation cannot acquire additional paths")
        if isinstance(index,bool) or not isinstance(index,(int,np.integer)) or not 0<=index<66 or index in self.queries:
            raise ValueError("Path is invalid or already acquired")
        self.queries.append(int(index))
        return damage_index(self._reference[index],self._test[index])

    def hidden_truth(self):
        if not self._ended:
            raise PermissionError("Reference location is sealed during policy execution")
        return self._truth

    def end_evaluation(self):
        self._ended=True
        return self.hidden_truth()


def geometry_order(K:np.ndarray,pairs:np.ndarray) -> list[int]:
    norms=np.linalg.norm(K,axis=1)
    normalized=K/np.maximum(norms[:,None],1e-12)
    distance=np.linalg.norm(SENSORS[pairs[:,0]]-SENSORS[pairs[:,1]],axis=1)
    selected=[int(np.argmax(distance))]
    while len(selected)<len(pairs):
        separation=1-np.max(normalized@normalized[selected].T,axis=1)
        separation[selected]=-np.inf
        selected.append(int(np.argmax(separation)))
    return selected


def summarize_weights(weights:np.ndarray,points:np.ndarray,location_logweights:np.ndarray) -> dict:
    if (weights.shape!=(len(points)+1,) or location_logweights.shape!=(len(points),)
            or not np.isfinite(weights).all() or np.any(weights<0)
            or not np.isclose(weights.sum(),1) or not np.isfinite(location_logweights).all()):
        raise ValueError("Model weights are not a valid finite distribution")
    damage_mass=float(weights[1:].sum())
    # Preserve a conditional location distribution even if the global damage
    # mass underflows. This remains hypothetical when the decision is healthy.
    conditional=np.exp(location_logweights-np.max(location_logweights))
    conditional/=conditional.sum()
    map_point=points[int(np.argmax(conditional))]
    distances=np.linalg.norm(points-map_point,axis=1)
    order=np.argsort(distances,kind="stable")
    radius=distances[order[min(int(np.searchsorted(np.cumsum(conditional[order]),.9)),len(order)-1)]]
    decision=None if abs(damage_mass-.5)<1e-12 else damage_mass > .5
    return {"map_m":map_point.tolist(),"damage_weight":damage_mass,
            "damage_decision":decision,"decision_abstained":decision is None,
            "location_supported_for_damage_decision":decision is True,
            "conditional_radius90_mm":float(radius*1000),
            "normalized_location_entropy":float(-np.sum(conditional*np.log(conditional+1e-300))/np.log(len(points))),
            "weights_are_field_calibrated":False}


def run_policy(oracle:MeasuredPathOracle,model:ResponseModel,K:np.ndarray,
               policy:str,order:list[int]|None=None,budget:int=32) -> dict:
    if not 1<=budget<=66 or policy not in {"cyclic","geometry_spread","training_static","random","adaptive_disagreement","full_bank_model"}:
        raise ValueError("Policy or recorded-path budget invalid")
    if (not np.isfinite([model.amplitude,model.noise_std]).all() or not 0<=model.amplitude<=1
            or model.noise_std<=0 or K.shape!=(66,GRID_SIZE**2)
            or not np.isfinite(K).all() or np.any(K<0) or np.any(K>1+1e-10)):
        raise ValueError("Response model or spatial kernel is invalid")
    if policy != "adaptive_disagreement" and (order is None or sorted(order)!=list(range(66))):
        raise ValueError("Fixed policy requires one complete recorded-path permutation")
    means=np.column_stack((np.zeros(66),model.amplitude*K))
    weights=np.r_[.5,np.full(K.shape[1],.5/K.shape[1])]
    log_weights=np.log(weights)
    traces=[];started=perf_counter()
    for step in range(budget):
        selection_started=perf_counter()
        if policy=="adaptive_disagreement":
            expectation=means@weights
            variance=np.maximum(0,(means*means)@weights-expectation*expectation)
            variance[oracle.queries]=-np.inf
            index=int(np.argmax(variance))
        else:index=int(order[step])
        selection_ms=(perf_counter()-selection_started)*1000
        try:
            observed=oracle.query(index)
            update=-.5*((observed-means[index])/model.noise_std)**2
            log_weights+=update
            log_weights-=np.max(log_weights)
            weights=np.exp(log_weights);weights/=weights.sum()
            accepted=True;error=None
        except ValueError as exc:
            observed=None;accepted=False;error=str(exc)
        state=summarize_weights(weights,grid_points(),log_weights[1:])
        traces.append({"budget":step+1,"path_index":index,"damage_index":observed,
                       "accepted":accepted,"error":error,"selection_latency_ms":selection_ms,**state})
    truth=oracle.end_evaluation()
    for row in traces:
        row["location_error_mm"]=float(np.linalg.norm(np.asarray(row["map_m"])-truth)*1000) if truth is not None else None
        row["conditional_region_covers_truth"]=bool(row["location_error_mm"] <= row["conditional_radius90_mm"]) if truth is not None else None
    return {"policy":policy,"query_count":len(oracle.queries),"selected_indices":oracle.queries.copy(),
            "failed_opportunities":sum(not x["accepted"] for x in traces),
            "elapsed_ms":(perf_counter()-started)*1000,"trace":traces}


def rapid_full_bank(oracle:MeasuredPathOracle,K:np.ndarray) -> dict:
    scores=np.zeros(K.shape[1]);failures=[]
    for index in range(66):
        try:scores+=oracle.query(index)*K[index]
        except ValueError as exc:failures.append({"path_index":index,"error":str(exc)})
    weights=scores/scores.sum() if scores.sum()>0 else np.full(len(scores),1/len(scores))
    point=grid_points()[int(np.argmax(weights))]
    truth=oracle.end_evaluation()
    return {"policy":"full_bank_RAPID","query_count":len(oracle.queries),"failures":failures,
            "map_m":point.tolist(),"location_error_mm":float(np.linalg.norm(point-truth)*1000) if truth is not None else None,
            "damage_decision":None,"healthy_detection_supported":False,"scores_are_probabilities":False}
