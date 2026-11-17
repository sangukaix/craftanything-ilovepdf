"""Check implemented tool entry points and every local link captured on home."""
import concurrent.futures
import argparse
import json
import re
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def audit(base_url='http://127.0.0.1:8766'):
 manifest=(ROOT/'app/src/app/ko/pdf-tools.ts').read_text(encoding='utf8')
 tools=[{'name':name,'route':'/ko/'+route+'/','source':(ROOT/'app/src/app/ko'/route/'page.tsx').exists()} for name,route in re.findall(r'\["([^"]+)","([^"]+)"\]',manifest)]
 captured=(ROOT/'app/src/app/captured-home.ts').read_text(encoding='utf8')
 html=json.loads(captured.split('=',1)[1].strip().rstrip(';'))
 links=sorted(set(re.findall(r'href=["\x27](/ko(?:/[^"\x27?#]*)?)["\x27]',html)))
 links=sorted(set(links+[tool['route'] for tool in tools]+['/ko/user/workflows/']))
 def check(route):
  try:
   with urllib.request.urlopen(base_url.rstrip('/')+route,timeout=10) as response:return {'route':route,'status':response.status}
  except Exception as error:return {'route':route,'status':getattr(error,'code',str(type(error).__name__))}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,links))
 report={'tools':tools,'coreToolCount':len(tools),'sourceMissing':[tool['route'] for tool in tools if not tool['source']],
         'localLinksChecked':len(results),'brokenLinks':[result for result in results if result['status']!=200],
         'links':results,'scope':'Entry points and navigation only. This does not certify complete feature parity or 98% visual similarity.'}
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8766');args=parser.parse_args()
 report=audit(args.base_url);(ROOT/'work').mkdir(exist_ok=True)
 (ROOT/'work/tool-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({key:report[key] for key in ['coreToolCount','localLinksChecked','sourceMissing','brokenLinks']},ensure_ascii=False))
 if report['sourceMissing'] or report['brokenLinks']:raise SystemExit(1)
