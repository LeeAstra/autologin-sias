"""Optional real UESTC/WLAN frozen smoke; HTTP stays on loopback, no tasks."""
import json, os, shutil, subprocess, sys, tempfile, threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sias_autologin.platforms.windows.network import target_wifi

def main():
    if target_wifi('UESTC')!='target_network':
        print('SKIP: a real verified UESTC connection is required')
        return
    requests=[]
    class Portal(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length',0)))
            requests.append(self.path)
            self.send_response(200);self.end_headers()
            self.wfile.write(b'{"success":true,"data":{"basic":{}}}')
    server=ThreadingHTTPServer(('127.0.0.1',0),Portal)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as folder:
            work=Path(folder);exe=work/'AutoLogin_SIAS_Headless.exe'
            shutil.copy2(ROOT/'packaging/dist'/exe.name,exe)
            env={k:v for k,v in os.environ.items() if k.upper() not in
                 ('WLAN_USER','WLAN_PWD','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')}
            env.update(http_proxy=f'http://127.0.0.1:{server.server_port}',no_proxy='',
                       WLAN_USER='synthetic-user',WLAN_PWD='synthetic-password')
            start=(datetime.now()-timedelta(minutes=1)).strftime('%H:%M:%S')
            end=(datetime.now()+timedelta(seconds=8)).strftime('%H:%M:%S')
            result=subprocess.run([str(exe),'--maintain','night','--window-start',start,
                                   '--window-end',end],cwd=work,env=env,timeout=45)
            assert result.returncode==0, result.returncode
            events=[json.loads(line.split('Maintenance event: ',1)[1]) for line in
                    (work/'auto_login_headless.log').read_text(encoding='utf-8').splitlines()
                    if 'Maintenance event: ' in line]
            assert any(e.get('state')=='authenticated' for e in events), events
            assert not any(e['event']=='login_result' for e in events), events
            assert requests and all(path.endswith('/homepage/info.php') for path in requests), requests
            print('PASS: production frozen WLAN API verifies real UESTC; only loopback state queries, zero login requests')
    finally:
        server.shutdown();server.server_close()
if __name__=='__main__':main()
