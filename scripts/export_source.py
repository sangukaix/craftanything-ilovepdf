"""Export an explicit source allowlist without local history, documents or secrets."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES=['README.md','REQUEST.md','CODEX_SETUP_REQUEST.md','THIRD_PARTY_NOTICES.md','LICENSE.md','AGENTS.md','.gitignore','.gitattributes','dependencies.lock.json','requirements.txt','setup.cmd','verify.cmd','start-local-pdf.cmd','start-pdf-service.cmd','start-cloudflare-share.cmd','stop-cloudflare-share.cmd']
APP_FILES=['AGENTS.md','package.json','package-lock.json','tsconfig.json','next-env.d.ts','next.config.mjs','postcss.config.mjs']
SCRIPTS=['account_service.py','account_store.py','audit_pdf_tools.py','pdf_advanced.py','pdf_columns.py','pdf_extra.py','pdf_layout.py','pdf_service.py','pdf_web.py','pdf_workflows.py','start_pdf_tools.py','runtime_config.py','doctor.py','install_runtime.py','verify_install.py','export_source.py','run_checks.py','setup.ps1','start_strata.ps1','python-requirements.in','python-requirements.lock','pdf-service-requirements.txt','test_pdf_client.cjs']

def candidates():
 paths=[ROOT/x for x in ROOT_FILES]+[ROOT/'app'/x for x in APP_FILES]+[ROOT/'scripts'/x for x in SCRIPTS+['share_gateway.py','share_cloudflare.py','verify_share.py']]
 paths+=list((ROOT/'scripts').glob('test_*.py'))
 paths+=list((ROOT/'docs').glob('*.md'))
 paths.append(ROOT/'docs/install-verification.json')
 paths+=[p for p in (ROOT/'app/src').rglob('*') if p.is_file() and p.suffix in {'.tsx','.ts','.css'}]
 paths+=[p for p in (ROOT/'app/public').rglob('*') if p.is_file()]
 paths+=list((ROOT/'.github/workflows').glob('*.yml'))
 return sorted(set(paths))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);args=parser.parse_args();target=args.destination.resolve()
 if target==ROOT or target.is_relative_to(ROOT):raise SystemExit('Use a new directory outside the working source.')
 target.mkdir(parents=True,exist_ok=True)
 # Existing installers in this verification checkout are ignored, but source files must match.
 records=[]
 for source in candidates():
  if not source.is_file():raise SystemExit('Missing source: '+str(source.relative_to(ROOT)))
  rel=source.relative_to(ROOT);parts={p.lower() for p in rel.parts}
  if parts & {'.local-data','.git','node_modules','work'} or source.suffix.lower() in {'.p12','.pfx','.key','.pem','.env','.sqlite','.db'}:raise SystemExit('Private path refused: '+str(rel))
  data=source.read_bytes()
  if len(data)>95*1024*1024:raise SystemExit('Oversized Git file: '+str(rel))
  if source.suffix in {'.md','.py','.json','.ts','.tsx','.cmd','.ps1','.yml','.txt'} and len(data)<3_000_000:
   text=data.decode('utf-8',errors='replace')
   if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-(?:proj-|svcacct-)[A-Za-z0-9_-]{30,}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9]{30,}',text):raise SystemExit('Possible credential found; refused: '+str(rel))
  output=target/rel;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
  records.append({'path':rel.as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 report={'schema':1,'files':records,'count':len(records),'bytes':sum(r['bytes'] for r in records)}
 (target/'SOURCE_MANIFEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'destination':str(target),'count':report['count'],'bytes':report['bytes']}))

if __name__=='__main__':main()
