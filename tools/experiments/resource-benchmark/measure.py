"""Read-only WLAN comparison; synthetic portal, never uses account credentials.
Requires psutil (measurement only). Run from the repository root on Windows.
"""
import argparse, ctypes, json, logging, math, subprocess, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor
from http.cookiejar import CookieJar
from datetime import datetime, timedelta
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sias_autologin.platforms.windows.network import target_wifi
from sias_autologin.runtime.monitor import maintain, LoginResult
from sias_autologin.core.portal import PortalClient, PortalSettings
from sias_autologin.core.service import ensure_authenticated

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend',choices=['baseline','native'],required=True)
    parser.add_argument('--mode',choices=['night','continuous'],required=True)
    parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--scenario',choices=['online','logout'],default='logout')
    args=parser.parse_args()
    if sys.platform != "win32": parser.error("This WLAN measurement requires Windows")
    if not math.isfinite(args.duration) or not 0 < args.duration < 86300:
        parser.error("Duration must be finite, positive and shorter than one day")
    children=[]
    if args.backend=='baseline':
        code=subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',
             'show','8809b05:src/sias_autologin/platforms/windows/network.py'],cwd=ROOT).decode()
        namespace={};exec(code,namespace)
        from types import SimpleNamespace
        def run(command,**kwargs):
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   creationflags=kwargs.get('creationflags',0))
            try:
                stdout,stderr=child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill();child.communicate()
                raise
            # Query kernel-retained peak memory after exit, avoiding a sampler
            # that would artificially inflate the baseline parent's CPU time.
            class Memory(ctypes.Structure):
                _fields_=[('cb',ctypes.c_uint32),('faults',ctypes.c_uint32)]+[
                    (name,ctypes.c_size_t) for name in ('peak_rss','rss','peak_pool','pool',
                    'peak_nonpool','nonpool','pagefile','peak_pagefile','private')]
            memory=Memory();memory.cb=ctypes.sizeof(memory)
            read_memory=ctypes.WinDLL('psapi').GetProcessMemoryInfo
            read_memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_uint32]
            if not read_memory(child._handle,ctypes.byref(memory),ctypes.sizeof(memory)):
                raise ctypes.WinError()
            peak=memory.peak_rss
            # The Windows process handle remains valid after process termination.
            class FILETIME(ctypes.Structure):
                _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
            stamps=[FILETIME() for _ in range(4)]
            function=ctypes.WinDLL('kernel32').GetProcessTimes
            function.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(FILETIME)]*4
            if not function(child._handle,*[ctypes.byref(x) for x in stamps]):
                raise ctypes.WinError()
            cpu=sum((x.high<<32)+x.low for x in stamps[2:])/1e7
            children.append({'cpu_seconds':cpu,'peak_rss':peak})
            return SimpleNamespace(stdout=stdout,stderr=stderr,returncode=child.returncode)
        namespace['subprocess']=SimpleNamespace(run=run,CREATE_NO_WINDOW=subprocess.CREATE_NO_WINDOW)
        probe=namespace['target_wifi']
    else: probe=target_wifi
    if probe('UESTC')!='target_network': raise RuntimeError('Connect UESTC; WLAN API must be available')
    children.clear()
    process=psutil.Process(); before=process.cpu_times(); handles_before=process.num_handles()
    began=time.monotonic(); stop=began+args.duration; logout=began+args.duration/2 if args.scenario=='logout' else float('inf')
    counters={'state_queries':0,'login_requests':0,'http_requests':0}
    restored=None; peaks=[]; probes=[]; submitted=False
    class Portal(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def answer(self):
            nonlocal submitted
            counters['http_requests']+=1
            self.rfile.read(int(self.headers.get('Content-Length',0)))
            self.send_response(200);self.end_headers()
            if self.path=='/homepage/info.php':
                counters['state_queries']+=1
                payload=({'success':False,'location':origin+'/ac_portal/needauth.html'}
                    if time.monotonic()>=logout and not submitted else {'success':True,'data':{'basic':{}}})
            elif self.path=='/ac_portal/login.php':
                counters['login_requests']+=1;submitted=True;payload={'success':True}
            else: payload={'success':True}
            self.wfile.write(json.dumps(payload).encode())
        do_GET=answer
        do_POST=answer
    server=ThreadingHTTPServer(('127.0.0.1',0),Portal)
    origin=f'http://127.0.0.1:{server.server_port}'
    threading.Thread(target=server.serve_forever,daemon=True).start()
    class LocalClient(PortalClient):
        def build_opener(self):
            return build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
    client=LocalClient(PortalSettings(origin,origin+'/page',origin+'/ac_portal/login.php',
                                    origin+'/jump',origin+'/homepage/info.php',5))
    def network():
        if time.monotonic()>=stop: return 'wrong_network'
        begin=time.perf_counter(); result=probe('UESTC');probes.append(time.perf_counter()-begin)
        peaks.append(process.memory_info().rss)
        if result != 'target_network':
            raise RuntimeError('Network conditions changed or measurement API failed; discard this run')
        return result
    def query(): return client.query_state()
    def login():
        nonlocal restored
        code=ensure_authenticated('synthetic-user','synthetic-password',client=client,
             require_auth_required=True,before_auth=lambda:network()=='target_network',logger=logger)
        if code==0 and submitted: restored=time.monotonic()
        return LoginResult(code,submitted,code==0)
    logger=logging.getLogger('benchmark');logger.setLevel(logging.INFO)
    log_counts={'state_events':0,'log_records':0}
    class CountLogs(logging.Handler):
        def emit(self,record):
            log_counts['log_records']+=1
            if record.getMessage().startswith('Maintenance state:'): log_counts['state_events']+=1
    logger.addHandler(CountLogs())
    now=datetime.now()
    try:
        maintain(mode=args.mode,network=network,query=query,login=login,logger=logger,
                 start=(now-timedelta(minutes=1)).time(),end=(now+timedelta(seconds=args.duration+60)).time())
        after=process.cpu_times()
    finally:
        server.shutdown();server.server_close()
    output=dict(backend=args.backend,mode=args.mode,scenario=args.scenario,interval=5 if args.mode=='night' else 30,
        elapsed_seconds=time.monotonic()-began,parent_cpu_seconds=after.user+after.system-before.user-before.system,
        child_cpu_seconds=sum(c['cpu_seconds'] for c in children),child_starts=len(children),
        parent_peak_rss=max(peaks,default=0),child_peak_rss=max((c['peak_rss'] for c in children),default=0),
        handles_delta=process.num_handles()-handles_before,probe_count=len(probes),
        probe_mean_seconds=sum(probes)/len(probes),recovery_seconds=None if restored is None else restored-logout,
        **counters,**log_counts)
    print(json.dumps(output))
if __name__=='__main__':main()
