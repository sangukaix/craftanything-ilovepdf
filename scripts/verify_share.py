"""Verify the current public tunnel with generated files, never private documents."""
import base64
import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import pymupdf
from runtime_config import ROOT

def main():
 local=ROOT/'.local-data/share';state=json.loads((local/'session.json').read_text(encoding='utf-8'));base=state['url']
 client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));checks=[]
 def request(path,body=None,origin=None,kind='application/json',csrf=None):
  headers={'Origin':origin or base,'Content-Type':kind}
  if csrf:headers['X-CSRF-Token']=csrf
  data=json.dumps(body).encode() if isinstance(body,dict) else body
  try:
   with client.open(urllib.request.Request(base+path,data=data,headers=headers),timeout=110) as response:return response.status,response.headers,response.read()
  except urllib.error.HTTPError as response:return response.code,response.headers,response.read()
 def verify(name,fn):
  started=time.monotonic();fn();checks.append({'name':name,'passed':True,'seconds':round(time.monotonic()-started,3)});print('PASS '+name,flush=True)
 def gate():
  assert request('/pdf-api/api/pdf/compress',{})[0]==401
  assert request('/share/login',urllib.parse.urlencode({'code':state['password'],'next':'/'}).encode(),kind='application/x-www-form-urlencoded')[0]==200
 verify('HTTPS gate and secure cookie login',gate)
 def boundaries():
  assert request('/.env')[0]==404
  assert request('/%2e%2e/.local-data/share/session.json')[0] in {400,403,404}
  assert request('/pdf-api/api/pdf/compress',{},origin='https://untrusted.invalid')[0]==403
  assert request('/pdf-api/../health',{})[0] in {400,403,404,405}
 verify('private paths and cross-origin rejection',boundaries)
 doc=pymupdf.open();doc.new_page().insert_text((50,80),'Cloudflare budget180 and deadline November17.');data=doc.tobytes();doc.close();payload={'pdf':base64.b64encode(data).decode()}
 def compress():
  status,_,body=request('/pdf-api/api/pdf/compress',payload);assert status==200
  with pymupdf.open(stream=body,filetype='pdf') as pdf:assert 'budget180' in pdf[0].get_text()
 verify('real PDF processing through public HTTPS',compress)
 def ai():
  status,_,body=request('/pdf-api/api/pdf/summarize',{**payload,'language':'en','length':'short'});assert status==200,(status,body[:300]);result=json.loads(body);assert '180' in result['summary'];assert result['model']
 verify('actual local AI through public HTTPS',ai)
 def account():
  status,_,body=request('/account-api/api/register',{'email':'cloudflare-'+str(time.time_ns())+'@example.invalid','password':'Synthetic-test-only-password'});assert status==200,(status,body[:200]);user=json.loads(body)
  assert request('/account-api/api/files',{'name':'synthetic.pdf',**payload})[0]==403
  status,_,body=request('/account-api/api/files',{'name':'synthetic.pdf',**payload},csrf=user['csrf']);assert status==200;item=json.loads(body)
  assert request('/account-api/api/files/'+item['id'])[2]==data
 verify('isolated vault and CSRF across HTTPS',account)
 (local/'public-verification.json').write_text(json.dumps({'date':'2026-11-17','scope':'Public Cloudflare edge on this PC, not a second physical device','checks':checks},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
