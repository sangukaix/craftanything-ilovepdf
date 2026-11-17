"""Verified, project-local Windows runtimes. Never edits system PATH or existing apps."""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'dependencies.lock.json').read_text(encoding='utf-8'))
LOCAL=ROOT/'.local-data';LOCAL.mkdir(exist_ok=True)

def fetch(name):
 asset=MANIFEST['assets'][name];folder=LOCAL/'downloads';folder.mkdir(exist_ok=True);target=folder/asset['filename']
 if target.exists():
  with target.open('rb') as cached: digest=hashlib.file_digest(cached,'sha256').hexdigest()
  if digest!=asset['sha256']:raise RuntimeError('Cached checksum mismatch: '+asset['filename'])
  return target
 print('Downloading '+asset['filename'],flush=True);partial=target.with_suffix(target.suffix+'.partial');errors=[]
 for url in [asset['url'],*asset.get('fallbackUrls',[])]:
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LocalPDF-Setup/1'}),timeout=60) as response,partial.open('wb') as output:shutil.copyfileobj(response,output,1024*1024)
   with partial.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
   if actual!=asset['sha256']:raise RuntimeError('Published checksum mismatch: '+asset['filename'])
   partial.replace(target);return target
  except Exception as e:errors.append(str(e))
 raise RuntimeError('Could not download '+asset['filename']+': '+'; '.join(errors))

def unzip(archive,target):
 target=Path(target).resolve();target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   resolved=(target/item.filename).resolve()
   if not resolved.is_relative_to(target) or ':' in item.filename:raise RuntimeError('Unsafe archive path')
  z.extractall(target)

def run(args,**kwargs):
 print('Running '+Path(str(args[0])).name,flush=True)
 result=subprocess.run([str(a) for a in args],cwd=ROOT,**kwargs)
 if result.returncode:raise RuntimeError('Command failed: '+Path(str(args[0])).name)

def api(url,body=None,timeout=5):
 req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)

def available(port):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=.5):return True
 except OSError:return False

def start_managed_ai(settings,timeout=180):
 """Called by installer and launcher; reuse only the expected compatible endpoint."""
 base=settings['baseUrl'].rstrip('/');model=settings['model']
 try:
  if model in [m['id'] for m in api(base+'/models')['data']]:return
 except Exception:pass
 provider=settings.get('provider')
 if provider=='existing':raise RuntimeError('The configured local AI server is not ready. Start it and retry.')
 if provider=='ollama':
  if available(11435):
   # Same program name is insufficient; verify the owning executable belongs here.
   import psutil
   expected=(ROOT/'tools/ollama/ollama.exe').resolve()
   owners=[c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==11435]
   if not owners or any(Path(psutil.Process(pid).exe()).resolve()!=expected for pid in owners if pid):raise RuntimeError('Port11435 belongs to another application; nothing was stopped.')
  else:
   env=os.environ.copy();env.update(OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(ROOT/'tools/ollama/models'))
   log=(LOCAL/'ollama.log').open('ab')
   subprocess.Popen([str(ROOT/'tools/ollama/ollama.exe'),'serve'],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);log.close()
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   try:api('http://127.0.0.1:11435/api/version');return
   except Exception:time.sleep(.4)
  raise RuntimeError('Ollama did not start; see .local-data/ollama.log')
 if provider=='strata':
  if available(8080):raise RuntimeError('Port8080 is occupied by a different local server. Use an Existing profile or another port.')
  log=(LOCAL/'strata.log').open('ab')
  subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/start_strata.ps1')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);log.close()
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   try:
    if model in [m['id'] for m in api(base+'/models')['data']]:return
   except Exception:pass
   time.sleep(1)
  raise RuntimeError('Strata is still preparing/downloading; see .local-data/strata.log, then rerun setup.')

def document_engines():
 lo=ROOT/'tools/libreoffice/runtime'
 if not (lo/'program/soffice.com').exists():
  less=ROOT/'tools/lessmsi'
  if not (less/'lessmsi.exe').exists():unzip(fetch('lessmsi'),less)
  destination=ROOT/'tools/libreoffice/extracted';destination.mkdir(parents=True,exist_ok=True)
  run([less/'lessmsi.exe','x',fetch('libreoffice'),str(destination)+os.sep],timeout=600,stdout=subprocess.DEVNULL)
  executable=next(destination.rglob('soffice.com'),None)
  if not executable:raise RuntimeError('LibreOffice archive did not contain soffice.com')
  shutil.copytree(executable.parent.parent,lo,dirs_exist_ok=True)
 java=next((ROOT/'tools/pdfa/java').rglob('java.exe'),None)
 if not java:
  unzip(fetch('java'),ROOT/'tools/pdfa/java');java=next((ROOT/'tools/pdfa/java').rglob('java.exe'))
 vera=ROOT/'tools/pdfa/verapdf'
 if not list((vera/'bin').glob('cli-*.jar')):
  folder=ROOT/'tools/pdfa/installer';unzip(fetch('verapdf'),folder);installer=next(folder.rglob('verapdf-izpack-installer-*.jar'))
  xml=LOCAL/'verapdf-install.xml';xml.write_text('<AutomatedInstallation langpack="eng"><com.izforge.izpack.panels.htmlhello.HTMLHelloPanel id="welcome"/><com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>'+escape(str(vera))+'</installpath></com.izforge.izpack.panels.target.TargetPanel><com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select"><pack index="0" name="veraPDF GUI" selected="false"/><pack index="1" name="veraPDF CLI" selected="true"/><pack index="2" name="veraPDF Documentation" selected="false"/><pack index="3" name="veraPDF Sample Plugins" selected="false"/></com.izforge.izpack.panels.packs.PacksPanel><com.izforge.izpack.panels.install.InstallPanel id="install"/><com.izforge.izpack.panels.finish.FinishPanel id="finish"/></AutomatedInstallation>',encoding='utf-8')
  run([java,'-jar',installer,xml],timeout=180)
  if not list((vera/'bin').glob('cli-*.jar')):raise RuntimeError('veraPDF CLI installation was incomplete')
 env=os.environ.copy();env['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'tools/html-browser')
 run([sys.executable,'-m','playwright','install','chromium','--only-shell'],env=env,timeout=600)

def install_ai(engine):
 model='qwen3.8-flash-next-iq2_xs'
 if engine in {'Auto','Existing'}:
  try:
   models=api('http://127.0.0.1:8080/v1/models')['data']
   if model in [m['id'] for m in models]:return {'provider':'existing','baseUrl':'http://127.0.0.1:8080/v1','model':model}
  except Exception:pass
  if engine=='Existing':raise RuntimeError('Expected local Strata/Qwen endpoint8080 is unavailable. Choose Ollama/Strata or configure PDF_AI_BASE_URL and PDF_AI_MODEL.')
  engine='Ollama'
 if engine=='None':return {'provider':'none','baseUrl':'http://127.0.0.1:8080/v1','model':model}
 if engine=='Strata':
  env=os.environ.copy();env.update(STRATA_NO_PATH='1',STRATA_DATA_DIR=str(ROOT/'tools/strata'),STRATA_FEED='https://github.com/Niko1221/Strata/releases/download/v0.2.13')
  run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',fetch('strata_installer')],env=env,timeout=600)
  run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'scripts/start_strata.ps1'],timeout=14400)
  return {'provider':'strata','baseUrl':'http://127.0.0.1:8080/v1','model':model}
 if engine=='Ollama':
  if not (ROOT/'tools/ollama/ollama.exe').exists():unzip(fetch('ollama'),ROOT/'tools/ollama')
  settings={'provider':'ollama','baseUrl':'http://127.0.0.1:11435/v1','model':'pdf-qwen3.5-4b-32k:latest'};start_managed_ai(settings)
  env=os.environ.copy();env.update(OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(ROOT/'tools/ollama/models'))
  run([ROOT/'tools/ollama/ollama.exe','pull',MANIFEST['aiDefault']],env=env,timeout=14400)
  modelfile=LOCAL/'Modelfile';modelfile.write_text('FROM '+MANIFEST['aiDefault']+'\nPARAMETER num_ctx 32768\nPARAMETER temperature 0\n',encoding='utf-8')
  run([ROOT/'tools/ollama/ollama.exe','create',settings['model'],'-f',modelfile],env=env,timeout=300);return settings
 raise RuntimeError('Unknown AI profile')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['Full','Core'],default='Full');parser.add_argument('--ai-engine',choices=['Auto','Existing','Ollama','Strata','None'],default='Auto');args=parser.parse_args()
 if os.name!='nt':raise RuntimeError('Automatic installation supports Windows x64. See docs/INSTALL.md for other systems.')
 if args.profile=='Full':document_engines()
 selected=install_ai('None' if args.profile=='Core' and args.ai_engine=='Auto' else args.ai_engine)
 config={'schema':1,'profile':args.profile,'ai':selected}
 path=LOCAL/'runtime.json'
 if path.exists():
  previous=json.loads(path.read_text(encoding='utf-8'))
  if previous!=config:(LOCAL/('runtime-before-'+str(int(time.time()))+'.json')).write_text(json.dumps(previous,indent=2),encoding='utf-8')
 path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Runtime ready: '+selected['provider']+' / '+selected['model'],flush=True)

if __name__=='__main__':
 try:main()
 except Exception as e:print('Setup failed: '+str(e),file=sys.stderr);raise SystemExit(1)
