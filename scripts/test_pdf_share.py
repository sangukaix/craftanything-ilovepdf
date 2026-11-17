import base64
import http.client
import json
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer
import pymupdf
from account_store import AccountStore
from account_service import create_server
from pdf_service import Handler
from share_gateway import ShareServer,COOKIE,ACCOUNT_ORIGIN

class ShareTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);out=self.folder/'out';out.mkdir();(out/'index.html').write_text('<h1>Shared site</h1>');(self.folder/'.env').write_text('SYNTHETIC_SECRET_ONLY')
  self.account=create_server(AccountStore(self.folder/'shared-accounts'),('127.0.0.1',0),ACCOUNT_ORIGIN)
  self.pdf=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  self.server=ShareServer(out,'synthetic-share-pass',self.account.server_port,address=('127.0.0.1',0),pdf_port=self.pdf.server_port);self.server.public_origin='https://share.example.invalid'
  for s in [self.account,self.pdf,self.server]:threading.Thread(target=s.serve_forever,daemon=True).start()
 def tearDown(self):
  for s in [self.server,self.pdf,self.account]:s.shutdown();s.server_close()
  self.temp.cleanup()
 def request(self,path,method='GET',body=None,cookie='',origin='https://share.example.invalid',host='share.example.invalid',kind='application/json',csrf=None):
  headers={'Host':host,'Origin':origin,'Content-Type':kind,'Cookie':cookie}
  if csrf:headers['X-CSRF-Token']=csrf
  if isinstance(body,dict):body=json.dumps(body).encode()
  client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);client.request(method,path,body=body,headers=headers);response=client.getresponse();data=response.read();status=response.status;hdr=dict(response.getheaders());client.close();return status,hdr,data
 def login(self):
  status,headers,_=self.request('/share/login','POST',urllib.parse.urlencode({'code':'synthetic-share-pass','next':'/'}),kind='application/x-www-form-urlencoded');self.assertEqual(status,303);self.assertIn('Secure',headers['Set-Cookie']);self.assertIn('HttpOnly',headers['Set-Cookie']);return headers['Set-Cookie'].split(';')[0]
 def test_gate_cookie_host_origin_and_path_boundaries(self):
  self.assertIn('공유 암호'.encode(),self.request('/')[2]);self.assertEqual(self.request('/pdf-api/api/pdf/compress','POST',{})[0],401)
  cookie=self.login();self.assertIn(b'Shared site',self.request('/',cookie=cookie)[2]);self.assertEqual(self.request('/',host='attacker.invalid',cookie=cookie)[0],403)
  self.assertEqual(self.request('/pdf-api/api/pdf/compress','POST',{},cookie,origin='https://attacker.invalid')[0],403)
  for path in ['/.env','/%2e%2e/.env','/../.env','/.local-data/share/session.json','/%5c..%5c.env']:
   self.assertEqual(self.request(path,cookie=cookie)[0],404)
  self.assertEqual(self.request('/account-api/api/me',cookie=COOKIE+'=forged')[0],401)
 def test_real_pdf_and_isolated_account_roundtrip(self):
  doc=pymupdf.open();doc.new_page().insert_text((40,70),'Shared synthetic PDF180');pdf=doc.tobytes();doc.close();cookie=self.login()
  code,_,data=self.request('/pdf-api/api/pdf/compress','POST',{'pdf':base64.b64encode(pdf).decode()},cookie);self.assertEqual(code,200)
  with pymupdf.open(stream=data,filetype='pdf') as result:self.assertIn('PDF180',result[0].get_text())
  self.assertEqual(self.request('/pdf-api/../.env','POST',{},cookie)[0],404)
  code,headers,data=self.request('/account-api/api/register','POST',{'email':'share@example.invalid','password':'Synthetic-password-only'},cookie);self.assertEqual(code,200);csrf=json.loads(data)['csrf'];cookie+='; '+headers['Set-Cookie'].split(';')[0]
  body={'name':'synthetic.pdf','pdf':base64.b64encode(pdf).decode()}
  self.assertEqual(self.request('/account-api/api/files','POST',body,cookie)[0],403)
  code,_,data=self.request('/account-api/api/files','POST',body,cookie,csrf=csrf);self.assertEqual(code,200);item=json.loads(data)
  self.assertEqual(self.request('/account-api/api/files/'+item['id'],cookie=cookie)[2],pdf)
  self.assertEqual(self.request('/account-api/api/payments/confirm','POST',{},cookie,csrf=csrf)[0],404)
 def test_wrong_password_is_rate_limited(self):
  for _ in range(24):self.assertEqual(self.request('/share/login','POST',b'code=wrong',kind='application/x-www-form-urlencoded')[0],200)
  self.assertEqual(self.request('/share/login','POST',b'code=wrong',kind='application/x-www-form-urlencoded')[0],429)

if __name__=='__main__':unittest.main()
