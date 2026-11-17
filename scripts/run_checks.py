"""Run the full document test suite; explicitly report disabled AI tests."""
import os
import subprocess
import sys
from runtime_config import ROOT,load_runtime

def main():
 env=os.environ.copy();env['PYTHONUTF8']='1'
 if load_runtime().get('ai',{}).get('provider')=='none':
  env['PDF_SKIP_AI_TESTS']='1';print('AI is disabled: the 2 actual model tests will be reported as skipped.',flush=True)
 for args in [[sys.executable,str(ROOT/'scripts/doctor.py'),'--profile','Full'],[sys.executable,'-m','unittest','discover','-s','scripts','-p','test_*.py','-v']]:
  result=subprocess.run(args,cwd=ROOT,env=env)
  if result.returncode:return result.returncode
 node=next((ROOT/'tools/node').glob('node-*-win-x64/node.exe'),None)
 return subprocess.run([str(node) if node else 'node',str(ROOT/'scripts/test_pdf_client.cjs')],cwd=ROOT,env=env).returncode

if __name__=='__main__':raise SystemExit(main())
