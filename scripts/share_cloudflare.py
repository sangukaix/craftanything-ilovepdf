"""Manage only this project's public Cloudflare Quick Tunnel."""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
import psutil
from runtime_config import ROOT,load_runtime

LOCAL=ROOT/'.local-data/share'
STATE=LOCAL/'session.json'

def get(url):
 with urllib.request.urlopen(url,timeout=2) as response:return json.load(response)
def status():
 try:
  state=json.loads(STATE.read_text(encoding='utf-8'));process=psutil.Process(state['pid'])
  if abs(process.create_time()-state['created'])>.1 or str(Path(__file__).resolve()) not in process.cmdline():return None
  if get('http://127.0.0.1:8770/share/health')['runId']!=state['runId']:return None
  return state
 except (OSError,ValueError,KeyError,psutil.Error):return None

def ensure_binary():
 from install_runtime import fetch,MANIFEST
 target=ROOT/'tools/cloudflared/cloudflared.exe'
 if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(fetch('cloudflared'),target)
 with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 if digest!=MANIFEST['assets']['cloudflared']['sha256']:raise RuntimeError('Cloudflared checksum mismatch. Nothing was executed.')
 return target

def tunnel_process(state):
 process=psutil.Process(state['tunnelPid'])
 if Path(process.exe()).resolve()!=(ROOT/'tools/cloudflared/cloudflared.exe').resolve():raise RuntimeError('Tunnel executable ownership mismatch.')
 if 'http://127.0.0.1:8770' not in process.cmdline():raise RuntimeError('Unexpected tunnel destination.')
 if state.get('tunnelCreated') and abs(process.create_time()-state['tunnelCreated'])>.1:raise RuntimeError('Tunnel process identity changed.')
 return process

def serve(resume=False):
 from share_gateway import ShareServer,ACCOUNT_ORIGIN
 from account_store import AccountStore
 from account_service import create_server
 LOCAL.mkdir(parents=True,exist_ok=True)
 if not (ROOT/'app/out/index.html').is_file():raise RuntimeError('Build the website first: setup.cmd')
 # No existing account database or private key is opened by this share process.
 with socket.socket() as probe:
  if probe.connect_ex(('127.0.0.1',8770))==0:raise RuntimeError('Port8770 is occupied; no process was stopped.')
 try:pdf_ready=get('http://127.0.0.1:8767/health').get('service')=='local-pdf'
 except Exception:pdf_ready=False
 if not pdf_ready:
  with socket.socket() as probe:
   if probe.connect_ex(('127.0.0.1',8767))==0:raise RuntimeError('Port8767 belongs to another application.')
  ai=load_runtime().get('ai',{})
  if ai.get('provider') in {'ollama','strata'}:
   from install_runtime import start_managed_ai
   start_managed_ai(ai,timeout=600)
  subprocess.Popen([sys.executable,str(ROOT/'scripts/pdf_service.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
  for _ in range(40):
   try:
    if get('http://127.0.0.1:8767/health').get('service')=='local-pdf':break
   except Exception:pass
   time.sleep(.25)
  else:raise RuntimeError('Document service did not start.')
 account=create_server(AccountStore(LOCAL/'accounts'),address=('127.0.0.1',0),origin=ACCOUNT_ORIGIN)
 threading.Thread(target=account.serve_forever,daemon=True).start()
 gateway=ShareServer(ROOT/'app/out',account.server_port)
 threading.Thread(target=gateway.serve_forever,daemon=True).start()
 binary=ensure_binary();config=LOCAL/'tunnel.yml';config.write_text('{}\n',encoding='utf-8')
 log_path=LOCAL/'cloudflare.log'
 if resume:
  previous=json.loads(STATE.read_text(encoding='utf-8'));tunnel=tunnel_process(previous)
 else:
  with log_path.open('wb') as output:
   tunnel=subprocess.Popen([str(binary),'--no-autoupdate','tunnel','--config',str(config),'--protocol','http2','--url','http://127.0.0.1:8770'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=subprocess.CREATE_NO_WINDOW)
 def alive():return tunnel.is_running() if isinstance(tunnel,psutil.Process) else tunnel.poll() is None
 try:
  deadline=time.monotonic()+90;url=previous['url'] if resume else None
  while time.monotonic()<deadline:
   if not alive():raise RuntimeError('Cloudflared exited; see .local-data/share/cloudflare.log')
   match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',log_path.read_text(encoding='utf-8',errors='replace'))
   if match:url=match.group(0);break
   time.sleep(.25)
  if not url:raise RuntimeError('Could not get a tunnel URL within90seconds.')
  gateway.public_origin=url
  state={'pid':os.getpid(),'created':psutil.Process().create_time(),'runId':gateway.run_id,'url':url,'public':True,'tunnelPid':tunnel.pid,'tunnelCreated':psutil.Process(tunnel.pid).create_time()}
  temporary=STATE.with_suffix('.tmp');temporary.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');temporary.replace(STATE)
  (LOCAL/'access.txt').write_text('URL: '+url+'\nNo share password required. Keep this PC running. Restart creates a new URL.\n',encoding='utf-8')
  while alive():time.sleep(1)
 finally:
  if alive():tunnel.terminate()
  gateway.shutdown();account.shutdown()

def show(state):print('URL: '+state['url']+'\n공유 암호 없이 프로젝트가 열립니다. PC를 켜 두세요. 종료: stop-cloudflare-share.cmd',flush=True)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','status','serve','reload'],default='start',nargs='?');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
 if args.action=='serve':serve(args.resume);return
 state=status()
 resume=False
 if args.action=='reload' and state:
  # Replace only this verified web process. Keep its existing Cloudflare URL alive.
  tunnel=tunnel_process(state);state['tunnelCreated']=tunnel.create_time()
  STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
  process=psutil.Process(state['pid']);process.terminate();process.wait(timeout=8)
  state=None;resume=True
 if args.action=='status':
  if state:show(state)
  else:print('현재 실행 중인 공유가 없습니다.');raise SystemExit(1)
 elif args.action=='stop':
  if not state:print('현재 실행 중인 공유가 없습니다.');return
  process=psutil.Process(state['pid']);children=process.children(recursive=True)
  tunnel=tunnel_process(state)
  if tunnel.pid not in {p.pid for p in children}:children.append(tunnel)
  for child in children:
   if not Path(child.exe()).resolve().is_relative_to(ROOT/'tools/cloudflared'):raise RuntimeError('Unexpected child process; nothing was stopped.')
  for child in children:child.terminate()
  process.terminate();process.wait(timeout=8);print('이 프로젝트의 공유 연결을 종료했습니다. 기존 PDF·AI 서비스는 유지됩니다.')
 else:
  if state:show(state);return
  LOCAL.mkdir(parents=True,exist_ok=True)
  with (LOCAL/'launcher.log').open('ab') as output:
   process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'serve',*(['--resume'] if resume else [])],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=subprocess.CREATE_NO_WINDOW)
  deadline=time.monotonic()+110
  while time.monotonic()<deadline:
   state=status()
   if state:show(state);return
   if process.poll() is not None:raise RuntimeError('공유 시작 실패: .local-data/share/launcher.log를 확인하세요.')
   time.sleep(.25)
  raise RuntimeError('공유 연결을 준비 중입니다. 잠시 후 start-cloudflare-share.cmd를 다시 실행하세요.')

if __name__=='__main__':
 try:main()
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
