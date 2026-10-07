"""Read-only WLAN comparison; synthetic portal, never uses account credentials.
Requires psutil (measurement only). Run from the repository root on Windows.
"""
import argparse, ctypes, importlib.util, json, logging, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sias_autologin.platforms.windows.network import target_wifi
from sias_autologin.runtime.monitor import maintain, LoginResult

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend',choices=['baseline','native'],required=True)
    parser.add_argument('--mode',choices=['night','continuous'],required=True)
    parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--scenario',choices=['online','logout'],default='logout')
    args=parser.parse_args()
    children=[]
    if args.backend=='baseline':
        code=subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',
             'show','8809b05:src/sias_autologin/platforms/windows/network.py'],cwd=ROOT).decode()
        namespace={};exec(code,namespace)
        from types import SimpleNamespace
        def run(command,**kwargs):
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   creationflags=kwargs.get('creationflags',0))
            process=psutil.Process(child.pid)
            peak=0
            deadline=time.monotonic()+5
            while child.poll() is None:
                if time.monotonic()>deadline:
                    child.kill();child.communicate()
                    raise subprocess.TimeoutExpired(command,5)
                try: peak=max(peak,process.memory_info().rss)
                except psutil.Error: pass
                time.sleep(.001)
            stdout,stderr=child.communicate(timeout=5)
            # The Windows process handle remains valid after process termination.
            class FILETIME(ctypes.Structure):
                _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
            stamps=[FILETIME() for _ in range(4)]
            function=ctypes.WinDLL('kernel32').GetProcessTimes
            function.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(FILETIME)]*4
            function(child._handle,*[ctypes.byref(x) for x in stamps])
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
    counters={'state_queries':0,'login_requests':0}; restored=None; peaks=[]; probes=[]
    def network():
        if time.monotonic()>=stop: return 'wrong_network'
        begin=time.perf_counter(); result=probe('UESTC');probes.append(time.perf_counter()-begin)
        peaks.append(process.memory_info().rss)
        return result
    def query():
        counters['state_queries']+=1
        return ('auth_required' if time.monotonic()>=logout and restored is None else 'authenticated','synthetic')
    def login():
        nonlocal restored
        # Match the runner/core: latest query and two fresh submission gates.
        state,_=query()
        if state!='auth_required': return LoginResult(8,False,False)
        if network()!='target_network' or network()!='target_network': return LoginResult(8,False,False)
        counters['login_requests']+=1;restored=time.monotonic()
        query()
        return LoginResult(0,True,True)
    logger=logging.getLogger('benchmark');logger.addHandler(logging.NullHandler())
    now=datetime.now()
    maintain(mode=args.mode,network=network,query=query,login=login,logger=logger,
             start=(now-timedelta(minutes=1)).time(),end=(now+timedelta(minutes=20)).time())
    after=process.cpu_times()
    output=dict(backend=args.backend,mode=args.mode,scenario=args.scenario,interval=5 if args.mode=='night' else 30,
        elapsed_seconds=time.monotonic()-began,parent_cpu_seconds=after.user+after.system-before.user-before.system,
        child_cpu_seconds=sum(c['cpu_seconds'] for c in children),child_starts=len(children),
        parent_peak_rss=max(peaks,default=0),child_peak_rss=max((c['peak_rss'] for c in children),default=0),
        handles_delta=process.num_handles()-handles_before,probe_count=len(probes),
        probe_mean_seconds=sum(probes)/len(probes),recovery_seconds=None if restored is None else restored-logout,
        **counters)
    print(json.dumps(output))
if __name__=='__main__':main()
