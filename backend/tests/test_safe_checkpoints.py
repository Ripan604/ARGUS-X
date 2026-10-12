import io
import json
import zipfile
from hashlib import sha256

import numpy as np
import pytest
import torch

from backend.app.models.checkpoints import load_forward_checkpoint, save_forward_checkpoint, load_forward_dataset
from backend.app.models.surrogate import ForwardSurrogate


def checkpoint():
    torch.manual_seed(17)
    model=ForwardSurrogate(24,15)
    return {'model_state':model.state_dict(),'input_size':24,'output_size':15,
            'input_mean':np.zeros(24),'input_std':np.ones(24),
            'target_mean':np.zeros(15),'target_std':np.ones(15),
            'metadata':{'samples':100,'feature_names':[f'f{i}' for i in range(15)]}}


def test_pickle_free_roundtrip_preserves_predictions(tmp_path):
    original=checkpoint()
    path=tmp_path/'safe.npz'
    save_forward_checkpoint(original,path)
    restored=load_forward_checkpoint(path)
    model1=ForwardSurrogate(24,15);model1.load_state_dict(original['model_state'])
    model2=ForwardSurrogate(24,15);model2.load_state_dict(restored['model_state'])
    x=torch.rand(3,24)
    torch.testing.assert_close(model1(x),model2(x),rtol=0,atol=0)


def test_legacy_checkpoint_never_calls_torch_deserializer(tmp_path,monkeypatch):
    path=tmp_path/'legacy.pt'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('archive/data.pkl',b'not even a pickle')
    monkeypatch.setattr(torch,'load',lambda *args,**kwargs: pytest.fail('Unsafe deserializer invoked'))
    with pytest.raises(ValueError,match='Legacy pickle'):
        load_forward_checkpoint(path)


def test_training_bank_rejects_object_metadata(tmp_path):
    path=tmp_path/'objects.npz'
    np.savez(path,inputs=np.ones((2,24)),targets=np.ones((2,15)),metadata=np.asarray({'bad':'object'},dtype=object))
    with pytest.raises(ValueError): load_forward_dataset(path)


@pytest.mark.parametrize('mutation',['hash','nonfinite','scale','shape'])
def test_untrusted_checkpoint_arrays_are_rejected_before_use(tmp_path,mutation):
    path=tmp_path/'safe.npz';save_forward_checkpoint(checkpoint(),path)
    with zipfile.ZipFile(path) as archive:
        members={name:archive.read(name) for name in archive.namelist()}
    manifest=json.loads(members['manifest.json'])
    name='normalizers/input_std.npy'
    if mutation=='hash': members[name]+=b'changed'
    else:
        arr=np.full(24,np.inf if mutation=='nonfinite' else 0,dtype=np.float32)
        if mutation=='shape': arr=np.ones(23,dtype=np.float32)
        buffer=io.BytesIO();np.save(buffer,arr,allow_pickle=False);members[name]=buffer.getvalue()
        manifest['sha256'][name]=sha256(members[name]).hexdigest()
        members['manifest.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(path,'w') as archive:
        for key,value in members.items(): archive.writestr(key,value)
    with pytest.raises(ValueError): load_forward_checkpoint(path)
