"""Start only this project's loopback services; never stop an existing process."""
import argparse
import json
import socket
import subprocess
import time
import urllib.request
import webbrowser
from runtime_config import load_runtime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def listening(port):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=.5):return True
 except OSError:return False

def service_ok():
 try:
  with urllib.request.urlopen('http://127.0.0.1:8767/health',timeout=1) as response:return json.load(response).get('service')=='local-pdf'
 except Exception:return False

def preview_ok():
 try:
  with urllib.request.urlopen('http://127.0.0.1:8766/',timeout=1) as response:return response.read()==(ROOT/'app/out/index.html').read_bytes()
 except Exception:return False

def account_ok():
 try:
  with urllib.request.urlopen('http://127.0.0.1:8768/health',timeout=1) as response:return json.load(response).get('service')=='local-pdf-account'
 except Exception:return False

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
 python=ROOT/'.pdf-service-venv/Scripts/python.exe'
 if not python.exists() or not (ROOT/'app/out/index.html').exists():raise RuntimeError('설치 또는 웹 빌드가 필요합니다. README.md를 확인하세요.')
 ai=load_runtime().get('ai',{})
 if ai.get('provider') in {'ollama','strata'}:
  from install_runtime import start_managed_ai
  print('설치한 로컬 AI 서버를 확인하고 있습니다…',flush=True)
  start_managed_ai(ai,timeout=600)
 plans=[(8767,service_ok,[str(python),'scripts/pdf_service.py']),
        (8768,account_ok,[str(python),'scripts/account_service.py']),
        (8766,preview_ok,[str(python),'-m','http.server','8766','--bind','127.0.0.1','--directory',str(ROOT/'app/out')])]
 # Check conflicts before starting either process.
 for port,check,_ in plans:
  if listening(port) and not check():raise RuntimeError(f'{port} 포트를 다른 프로그램이 사용 중입니다. 기존 프로그램은 변경하지 않았습니다.')
 for port,check,command in plans:
  if not listening(port):subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
  deadline=time.monotonic()+12
  while not check():
   if time.monotonic()>deadline:raise RuntimeError(f'{port} 서비스가 시작되지 않았습니다. README.md의 수동 실행 방법을 확인하세요.')
   time.sleep(.2)
 print('PDF 도구 실행 준비 완료: http://127.0.0.1:8766/')
 print('로컬 요약·번역을 사용하려면 기존 Qwen 모델 서버도 실행되어 있어야 합니다.')
 if not args.no_browser:webbrowser.open('http://127.0.0.1:8766/')

if __name__=='__main__':
 try:main()
 except Exception as error:print(str(error));raise SystemExit(1)
