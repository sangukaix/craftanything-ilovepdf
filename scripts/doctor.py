"""Machine-readable feature readiness, without reading account or credential files."""
import argparse
import importlib
import json
import platform
import sys
import urllib.request
from pathlib import Path
from runtime_config import ROOT,load_runtime,ai_settings

def inspect(profile='Full'):
 checks=[]
 def check(name,passed,detail='',required=True):checks.append({'name':name,'passed':bool(passed),'detail':detail,'required':required})
 check('windows-x64',sys.platform=='win32' and platform.machine().lower() in {'amd64','x86_64'},platform.platform())
 for name in ['pypdf','pymupdf','pdf2docx','docx','pptx','cryptography','pyhanko','playwright','PIL','openpyxl','cv2']:
  try:importlib.import_module(name);check('python:'+name,True)
  except Exception as e:check('python:'+name,False,str(e))
 for name in ['app/public/font/noto-sans-kr-bmp.ttf','app/public/ocr/lang/eng.traineddata','app/public/ocr/lang/kor.traineddata','app/public/pdfjs/pdf.worker.min.mjs','app/out/index.html']:
  check(name,(ROOT/name).is_file())
 check('LibreOffice',(ROOT/'tools/libreoffice/runtime/program/soffice.com').is_file(),required=profile=='Full')
 check('Java21',any((ROOT/'tools/pdfa/java').rglob('java.exe')),required=profile=='Full')
 check('veraPDF',any((ROOT/'tools/pdfa/verapdf/bin').glob('cli-*.jar')),required=profile=='Full')
 check('Chromium',any((ROOT/'tools/html-browser').rglob('chrome-headless-shell.exe')),required=profile=='Full')
 settings=load_runtime();enabled=settings.get('ai',{}).get('provider')!='none'
 if enabled:
  try:
   base,model=ai_settings()
   with urllib.request.urlopen(base+'/models',timeout=5) as response:models=json.load(response)['data']
   check('local-AI',model in [m['id'] for m in models],model,required=profile=='Full')
  except Exception as e:check('local-AI',False,str(e),required=profile=='Full')
 else:check('local-AI-disabled',True,'Explicitly disabled. Summary/translation unavailable.',required=False)
 report={'profile':profile,'python':sys.version.split()[0],'checks':checks,'ok':all(c['passed'] for c in checks if c['required'])}
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',choices=['Full','Core'],default='Full');args=p.parse_args();result=inspect(args.profile)
 local=ROOT/'.local-data';local.mkdir(exist_ok=True);(local/'doctor.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 for item in result['checks']:print(('OK ' if item['passed'] else 'MISSING ')+item['name']+(' (optional)' if not item['required'] else ''))
 raise SystemExit(0 if result['ok'] else 1)

if __name__=='__main__':main()
