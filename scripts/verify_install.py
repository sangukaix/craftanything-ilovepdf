"""Post-install integration check with generated documents and isolated account storage."""
import argparse
import io
import json
import re
import tempfile
import time
from pathlib import Path
import pymupdf
from runtime_config import ROOT,load_runtime

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['Full','Core'],default='Full');args=parser.parse_args()
 out=ROOT/'.local-data/verification';out.mkdir(parents=True,exist_ok=True);checks=[]
 def verify(name,task):
  started=time.monotonic()
  try:task();checks.append({'name':name,'passed':True,'seconds':round(time.monotonic()-started,3)});print('PASS '+name,flush=True)
  except Exception as e:checks.append({'name':name,'passed':False,'error':str(e)});print('FAIL '+name+': '+str(e),flush=True)
  (out/'result.json').write_text(json.dumps({'profile':args.profile,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
 from pdf_service import process_pdf,convert_to_word,convert_to_powerpoint
 from pdf_extra import office_pdf,translate_pdf
 from pdf_advanced import pdfa_convert
 from pdf_web import html_to_pdf,summarize_pdf
 from test_pdf_extra import office_samples,sample_pdf
 from test_pdf_columns import fixture,request
 from pdf_layout import reflow_paragraph
 source=sample_pdf()
 def core():
  compressed=process_pdf('compress',source);assert compressed.startswith(b'%PDF-')
  protected=process_pdf('protect',source,'SYNTHETIC-ONLY');unlocked=process_pdf('unlock',protected,'SYNTHETIC-ONLY');assert unlocked.startswith(b'%PDF-')
 verify('compress/protect/unlock',core)
 def conversions():
  assert convert_to_word(source)[:2]==b'PK';assert convert_to_powerpoint(source)[:2]==b'PK'
 verify('editable Word and PowerPoint export',conversions)
 def columns():
  for n in (2,3):
   data=fixture(n);output,report=reflow_paragraph(data,request(data,n,260));(out/f'{n}-columns.pdf').write_bytes(output)
   with pymupdf.open(stream=output,filetype='pdf') as doc:assert re.sub(r'\s+',' ',' '.join(p.get_text() for p in doc)).count('Expanded item.')==260
 verify('2/3-column document flow',columns)
 def accounts():
  from account_store import AccountStore
  with tempfile.TemporaryDirectory(dir=out) as folder:
   store=AccountStore(folder);token,user=store.register('setup@example.invalid','SYNTHETIC-password-only');item=store.upload(user['id'],'test.pdf',source);assert store.download(user['id'],item['id'])[1]==source
   order=store.create_order(user['id'],'storage-test','demo');store.demo_result(user['id'],order['id'],'DONE');until=store.me(token)['paidUntil'];store.demo_result(user['id'],order['id'],'DONE');assert store.me(token)['paidUntil']==until
 verify('account vault and replay-safe demo payment',accounts)
 if args.profile=='Full':
  def office():
   for ext,data in office_samples().items():assert office_pdf(data,ext).startswith(b'%PDF-')
  verify('DOCX/XLSX/PPTX to PDF',office)
  def archive_pdf():
   output,report=pdfa_convert(source);assert output.startswith(b'%PDF-')
  verify('PDF/A2b with veraPDF validation',archive_pdf)
  def html():
   output,report=html_to_pdf({'html':'<h1>Installation test</h1><p>Invoice180</p>'});assert output.startswith(b'%PDF-')
  verify('sandboxed HTML to PDF',html)
  if load_runtime().get('ai',{}).get('provider')!='none':
   def ai():
    doc=pymupdf.open();doc.new_page().insert_text((50,80),'The budget is180 units. The deadline is November17.');data=doc.tobytes();doc.close();result=summarize_pdf(data,{'language':'en','length':'short'});assert result['summary'].strip();assert translate_pdf(data,'ko').startswith(b'%PDF-')
   verify('actual local AI summary/translation',ai)
 if not all(c['passed'] for c in checks):raise SystemExit(1)
 print('All installation checks passed. Synthetic results: .local-data/verification',flush=True)

if __name__=='__main__':main()
