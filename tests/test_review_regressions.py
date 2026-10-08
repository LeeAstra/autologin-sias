import json
import logging
from datetime import datetime, timedelta, time
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sias_autologin.core.authentication import response_indicates_success
from sias_autologin.core.service import ensure_authenticated
from sias_autologin.runtime.monitor import maintain, LoginResult
from test_portable_core import FakeClient
from sias_autologin.platforms.windows import runner

class ReviewRegressionTests(unittest.TestCase):
    def test_json_text_failure_negation_conflict_and_success(self):
        cases=[({'message':'login unsuccessful'},False),
               ({'msg':'login failed: already online'},False),
               ({'message':'login not successful'},False),
               ({'message':'not login ok'},False),
               ({'message':'没有登录成功'},False),
               ({'message':'login successful'},True),
               ({'message':'login ok'},True),
               ({'message':'success'},None),
               ({'message':'already online'},None),
               ({'message':'login successful but error'},None),
               ({'success':False,'message':'login successful'},False),
               ({'success':True,'result':False},None),
               ({'success':True,'message':'login unsuccessful'},True)]
        for message,expected in cases:
            with self.subTest(message=message):
                self.assertIs(response_indicates_success(json.dumps(message).encode())[0],expected)

    def test_success_text_requires_complete_known_format(self):
        for text in ('login success: false','login successful? no','login successful? yes',
                     'login successful: false','login success = false','prefix login successful',
                     'login successful suffix','login successful; denied','登录成功？否'):
            for body in (text.encode(),json.dumps({'message':text}).encode()):
                with self.subTest(text=text,body=body):
                    self.assertIsNone(response_indicates_success(body)[0])
        for text in ('login success','login successful','login ok','logon success','认证成功'):
            self.assertIs(response_indicates_success(text.encode())[0],True)

    def test_ambiguous_success_cannot_validate_online_credentials(self):
        for text in ('login success: false','login successful? no'):
            client=FakeClient(['authenticated','authenticated'])
            original=client.request
            def request(opener,url,*,data=None):
                original(opener,url,data=data)
                return 200,json.dumps({'message':text}).encode() if url==client.settings.login_url else b'1'
            client.request=request
            self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client,
                             validate_credentials=True),8)
            self.assertEqual(len(client.calls),3)

    def test_javascript_and_duplicate_structured_fields_do_not_use_success_text(self):
        for body,expected in [(b"{'result':false,'msg':'logon success'}",False),
                              (b"{'success':'false','msg':'logon success'}",False),
                              (b"{'success':true,'result':false}",None),
                              (b"{'success':unknown,'msg':'logon success'}",None),
                              (b'{"success":false,"success":true}',None)]:
            with self.subTest(body=body):
                self.assertIs(response_indicates_success(body)[0],expected)

    def test_incomplete_or_non_literal_portal_objects_are_unknown(self):
        for body in (b'{"success":true', b"{'success':true+1}", b"{'success':true,'msg':'login successful',broken}",
                     b"{'success':true,'success':false}"):
            with self.subTest(body=body):
                self.assertIsNone(response_indicates_success(body)[0])

    def test_forced_online_validation_cannot_accept_failure_message(self):
        for body in (b'{"message":"login unsuccessful"}',b'{"msg":"login failed: already online"}',
                     b'{"success":false,"message":"login successful"}'):
            with self.subTest(body=body):
                client=FakeClient(['authenticated','authenticated'])
                original=client.request
                def request(opener,url,*,data=None):
                    original(opener,url,data=data)
                    return 200,body if url==client.settings.login_url else b'1'
                client.request=request
                self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client,validate_credentials=True),5)
                self.assertEqual(len(client.calls),3)

    def test_strict_policy_latest_unknown_authenticated_or_required(self):
        for state,expected,requests in [('unknown',8,0),('authenticated',0,0),('auth_required',0,3)]:
            with self.subTest(state=state):
                client=FakeClient([state,'authenticated'])
                self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client,require_auth_required=True),expected)
                self.assertEqual(len(client.calls),requests)

    def test_legacy_unknown_and_installer_force_policies_are_retained(self):
        client=FakeClient(['unknown','authenticated'])
        self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client),0)
        self.assertEqual(len(client.calls),3)
        client=FakeClient(['authenticated','authenticated'])
        self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client,validate_credentials=True),0)
        self.assertEqual(len(client.calls),3)

    def test_pre_submission_gate_after_slow_portal_fetch(self):
        client=FakeClient(['auth_required']); permission=[True]; submitted=[]
        original=client.request
        def request(*args,**kwargs):
            result=original(*args,**kwargs); permission[0]=False; return result
        client.request=request
        self.assertEqual(ensure_authenticated('synthetic','synthetic',client=client,require_auth_required=True,
                         before_auth=lambda:permission[0],on_submit=lambda:submitted.append(1)),8)
        self.assertEqual(len(client.calls),1)
        self.assertEqual(submitted,[])

    def test_loop_latest_state_is_rechecked_before_authentication(self):
        for latest,count in [('unknown',0),('authenticated',0),('auth_required',3)]:
            with self.subTest(latest=latest):
                clock=[datetime(2026,1,1,3,14,59)]; client=FakeClient([latest,'authenticated'])
                def login():
                    submitted=[]
                    code=ensure_authenticated('synthetic','synthetic',client=client,require_auth_required=True,
                                              on_submit=lambda:submitted.append(True))
                    return LoginResult(code,bool(submitted),code==0)
                maintain(mode='night',network=lambda:'target_network',query=lambda:('auth_required','fixture'),login=login,
                         logger=logging.getLogger('test'),clock=lambda:clock[0],sleep=lambda seconds:clock.__setitem__(0,clock[0]+timedelta(seconds=seconds)))
                self.assertEqual(len(client.calls),count)

    def test_network_and_query_must_not_start_authentication_outside_window(self):
        for advance_in in ('first_network','query','second_network'):
            for seconds in (1,2):
                with self.subTest(advance_in=advance_in,seconds=seconds):
                    clock=[datetime(2026,1,1,3,14,59)]; probes=[0]; calls=[]
                    def network():
                        probes[0]+=1
                        if (advance_in=='first_network' and probes[0]==1) or (advance_in=='second_network' and probes[0]==2):
                            clock[0]+=timedelta(seconds=seconds)
                        return 'target_network'
                    def query():
                        if advance_in=='query': clock[0]+=timedelta(seconds=seconds)
                        return 'auth_required','fixture'
                    maintain(mode='night',network=network,query=query,login=lambda:calls.append(1),logger=logging.getLogger('test'),
                             clock=lambda:clock[0],sleep=lambda seconds:clock.__setitem__(0,clock[0]+timedelta(seconds=seconds)))
                    self.assertEqual(calls,[])

    def test_cross_midnight_probe_reaching_end_does_not_login(self):
        clock=[datetime(2026,1,2,0,59,59)]; probes=[0]; calls=[]
        def network():
            probes[0]+=1
            if probes[0]==2: clock[0]+=timedelta(seconds=1)
            return 'target_network'
        maintain(mode='night',network=network,query=lambda:('auth_required','fixture'),login=lambda:calls.append(1),
                 logger=logging.getLogger('test'),start=time(23),end=time(1),clock=lambda:clock[0],sleep=lambda _:None)
        self.assertEqual(clock[0].time(),time(1))
        self.assertEqual(calls,[])

    def test_cross_midnight_window_end_and_inflight_completion(self):
        clock=[datetime(2026,1,2,0,59,59)]; calls=[]
        def login():
            calls.append(clock[0]); clock[0]+=timedelta(seconds=2)
            return LoginResult(0,True,True)
        maintain(mode='night',network=lambda:'target_network',query=lambda:('auth_required','fixture'),login=login,
                 logger=logging.getLogger('test'),start=time(23),end=time(1),clock=lambda:clock[0],sleep=lambda _:None)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].time(),time(0,59,59))

    def test_windows_adapter_requires_latest_state_and_gates_submission(self):
        args=SimpleNamespace(maintain='night',window_start='02:55',window_end='03:15')
        tick=[datetime(2026,1,1,3,14,59)]; captured=[]
        def run_login(**kwargs):
            captured.append(kwargs)
            self.assertTrue(kwargs['require_auth_required'])
            self.assertFalse(kwargs['before_auth']())
            return 8
        app=SimpleNamespace(LOGGER=logging.getLogger('adapter-test'),run_login=run_login,query_authentication_state=lambda:('auth_required','fixture'))
        def network(ssid):
            tick[0]+=timedelta(seconds=2)
            return 'target_network'
        with patch.object(runner.os,'name','nt'), patch.object(runner.ctypes,'WinDLL',create=True) as dll, \
             patch.object(runner.ctypes,'get_last_error',return_value=0,create=True), \
             patch.object(runner,'datetime') as date, patch.object(runner,'target_wifi',side_effect=network), \
             patch.object(runner,'maintain') as loop:
            dll.return_value.CreateMutexW.return_value=1
            date.now.side_effect=lambda:tick[0]
            def invoke(**kwargs):
                result=kwargs['login']()
                self.assertFalse(result.submitted); self.assertFalse(result.confirmed)
                return result.code
            loop.side_effect=invoke
            self.assertEqual(runner.run(app,args),8)
        self.assertEqual(len(captured),1)

    def test_loop_records_run_boundaries_and_submission_separately(self):
        clock=[datetime(2026,1,1,3,14,59)]
        with self.assertLogs('evidence-test',level='INFO') as output:
            maintain(mode='night',network=lambda:'target_network',query=lambda:('auth_required','fixture'),
                     login=lambda:LoginResult(8,False,False),logger=logging.getLogger('evidence-test'),run_id='fixture',version='fixture',
                     clock=lambda:clock[0],sleep=lambda seconds:clock.__setitem__(0,clock[0]+timedelta(seconds=seconds)))
        records=[json.loads(line.split('Maintenance event: ',1)[1]) for line in output.output if 'Maintenance event: ' in line]
        self.assertEqual(records[0]['event'],'start'); self.assertEqual(records[-1]['event'],'end')
        self.assertTrue(all(r['run_id']=='fixture' and r['timestamp'] for r in records))
        result=next(r for r in records if r['event']=='login_result')
        self.assertFalse(result['submitted']); self.assertFalse(result['confirmed'])

if __name__=='__main__': unittest.main()
