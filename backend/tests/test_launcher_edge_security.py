import sys
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request

import pytest
import run_argus
import run_edge_node


def test_authenticated_edge_redirects_are_refused():
    request=Request('https://argus.example/session',headers={'Authorization':'Bearer '+'x'*40})
    with pytest.raises(HTTPError,match='Redirect refused'):
        run_edge_node.NoRedirects().redirect_request(request,None,302,'Found',{},'https://other.example/')


@pytest.mark.parametrize('server',['file:///etc/passwd','https://secret@host.example','https://host.example/?key=x'])
def test_edge_rejects_unsafe_server_addresses(server):
    with pytest.raises(ValueError): run_edge_node.request_json(server,'/health')


def test_edge_acquires_each_new_recommendation_and_registers_once(monkeypatch):
    monkeypatch.setattr(sys,'argv',['run_edge_node.py','--server','http://localhost:8001','--session','session','--auto-capture'])
    count=0;captured=[];registered=[];sleeps=[]
    def request(server,path,method='GET',payload=None,token=None):
        nonlocal count
        if path=='/api/probe/register': registered.append(payload);return {}
        if path=='/api/probe/measurement':
            captured.append(payload);count+=1
            return {'state':{'status':{'experiment_count':count}},'quality':{}}
        return {'status':{'experiment_count':count,'should_stop':False},'recommendation':{
            'action_type':'diagnostic','experiment':{'source_x':0.1,'source_y':0.2,'receiver_x':0.9,'receiver_y':0.3,'duration_s':0.12}}}
    def sleep(delay):
        sleeps.append(delay)
        if len(sleeps)==2: raise KeyboardInterrupt
    monkeypatch.setattr(run_edge_node,'request_json',request)
    monkeypatch.setattr(run_edge_node,'capture_microphone',lambda *_: [0.1]*1920)
    monkeypatch.setattr(run_edge_node.time,'sleep',sleep)
    run_edge_node.main()
    assert len(captured)==2
    assert len(registered)==1


def test_windows_launcher_stops_its_owned_process_tree(monkeypatch):
    calls=[]
    monkeypatch.setattr(run_argus.sys,'platform','win32')
    monkeypatch.setattr(run_argus.subprocess,'run',lambda args,**kwargs: (calls.append(args),SimpleNamespace(returncode=0))[1])
    process=SimpleNamespace(pid=12345,poll=lambda:None,wait=lambda **kwargs:None)
    run_argus.terminate(process)
    assert calls==[['taskkill','/PID','12345','/T','/F']]


def test_launcher_frontend_does_not_receive_operator_key(monkeypatch):
    monkeypatch.setattr(sys,'argv',['run_argus.py','--lan'])
    monkeypatch.setenv('ARGUS_API_TOKEN','x'*40)
    monkeypatch.setattr(run_argus,'local_network_address',lambda:'192.168.1.25')
    monkeypatch.setattr(run_argus.shutil,'which',lambda _: 'npm.cmd')
    monkeypatch.setattr(run_argus.signal,'signal',lambda *_:None)
    monkeypatch.setattr(run_argus,'terminate',lambda _:None)
    calls=[]
    def launch(args,**kwargs):
        calls.append((args,kwargs))
        return SimpleNamespace(poll=lambda:None)
    monkeypatch.setattr(run_argus.subprocess,'Popen',launch)
    def stop(_): raise KeyboardInterrupt
    monkeypatch.setattr(run_argus.time,'sleep',stop)
    with pytest.raises(KeyboardInterrupt): run_argus.main()
    assert calls[0][1]['env']['ARGUS_API_TOKEN']=='x'*40
    assert 'ARGUS_API_TOKEN' not in calls[1][1]['env']
    assert calls[0][1]['env']['ARGUS_NETWORK_MODE']=='lan'
    assert calls[1][0][calls[1][0].index('--hostname')+1]=='0.0.0.0'
