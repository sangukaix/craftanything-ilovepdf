import base64
import concurrent.futures
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from account_store import AccountStore,AccountError,TossSandbox
from account_service import create_server

PDF=b'%PDF-1.7\nSYNTHETIC TEST DOCUMENT ONLY\n%%EOF'

class FakeToss(TossSandbox):
 def __init__(self):super().__init__('test_gck_synthetic','test_gsk_synthetic');self.proof={};self.calls=[]
 def confirm(self,key,order_id,amount,idempotency):self.calls.append((key,order_id,amount,idempotency));return self.proof
 def retrieve(self,key):return self.proof

class StoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.provider=FakeToss();self.store=AccountStore(self.temp.name,self.provider)
  self.token,self.user=self.store.register('alpha@example.invalid','Synthetic-pass-2026');self.other_token,self.other=self.store.register('beta@example.invalid','Other-synthetic-pass')
 def tearDown(self):self.temp.cleanup()
 def test_password_hash_login_logout(self):
  with self.store.db() as db:
   row=db.execute('SELECT * FROM users WHERE id=?',(self.user['id'],)).fetchone();self.assertNotEqual(bytes(row['password']),b'Synthetic-pass-2026')
  with self.assertRaises(AccountError):self.store.login('alpha@example.invalid','wrong-password')
  token,user=self.store.login('ALPHA@example.invalid','Synthetic-pass-2026');self.assertEqual(user['id'],self.user['id']);self.store.logout(token)
  with self.assertRaises(AccountError):self.store.me(token)
 def test_encrypted_storage_roundtrip_and_cross_account(self):
  item=self.store.upload(self.user['id'],'시험.pdf',PDF);self.assertEqual(self.store.download(self.user['id'],item['id'])[1],PDF)
  with self.store.db() as db:body=bytes(db.execute('SELECT body FROM files').fetchone()[0]);self.assertNotIn(PDF,body)
  for operation in [self.store.download,self.store.delete]:
   with self.assertRaises(AccountError):operation(self.other['id'],item['id'])
  self.assertEqual(self.store.list_files(self.other['id']),[]);self.store.delete(self.user['id'],item['id']);self.assertEqual(self.store.list_files(self.user['id']),[])
 def test_vault_persists_across_restart(self):
  item=self.store.upload(self.user['id'],'saved.pdf',PDF);reopened=AccountStore(self.temp.name);self.assertEqual(reopened.download(self.user['id'],item['id'])[1],PDF)
 def test_path_rejection_and_quota(self):
  for name in ['../outside.pdf','C:\\private.pdf','bad\nname.pdf']:
   with self.assertRaises(AccountError):self.store.upload(self.user['id'],name,PDF)
  for i in range(5):self.store.upload(self.user['id'],f'{i}.pdf',PDF)
  with self.assertRaises(AccountError):self.store.upload(self.user['id'],'six.pdf',PDF)
 def test_demo_success_concurrent_replay_exactly_once(self):
  order=self.store.create_order(self.user['id'],'storage-test','demo')
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:self.store.demo_result(self.user['id'],order['id'],'DONE'),range(8)))
  until=self.store.me(self.token)['paidUntil'];self.store.demo_result(self.user['id'],order['id'],'DONE');self.assertEqual(until,self.store.me(self.token)['paidUntil']);self.assertEqual(self.store.me(self.token)['plan'],'test-expanded')
  self.assertEqual(self.store.order(self.user['id'],order['id'])['applied'],1)
 def test_failure_cancel_and_cross_account_no_entitlement(self):
  for outcome in ['FAILED','CANCELED']:
   order=self.store.create_order(self.user['id'],'storage-test','demo');self.store.demo_result(self.user['id'],order['id'],outcome)
   with self.assertRaises(AccountError):self.store.demo_result(self.user['id'],order['id'],'DONE')
  order=self.store.create_order(self.user['id'],'storage-test','demo')
  with self.assertRaises(AccountError):self.store.demo_result(self.other['id'],order['id'],'DONE')
  self.assertEqual(self.store.me(self.token)['paidUntil'],0)
 def test_toss_confirm_tamper_and_verified_webhook(self):
  order=self.store.create_order(self.user['id'],'storage-test','toss');proof={'orderId':order['id'],'paymentKey':'sandbox_proof_1','totalAmount':1000,'currency':'KRW','status':'DONE'}
  self.provider.proof=proof
  with self.assertRaises(AccountError):self.store.confirm(self.user['id'],order['id'],'sandbox_proof_1',1)
  self.assertEqual(self.provider.calls,[])
  for changed in [{'totalAmount':1},{'currency':'USD'},{'status':'READY'},{'orderId':'unrelated'},{'paymentKey':'different'}]:
   self.provider.proof={**proof,**changed}
   with self.assertRaises(AccountError):self.store.confirm(self.user['id'],order['id'],'sandbox_proof_1',1000)
   self.assertEqual(self.store.me(self.token)['paidUntil'],0)
  self.provider.proof=proof;self.store.reconcile('sandbox_proof_1');until=self.store.me(self.token)['paidUntil'];self.store.confirm(self.user['id'],order['id'],'sandbox_proof_1',1000);self.assertEqual(until,self.store.me(self.token)['paidUntil'])
  self.assertEqual(self.provider.calls[-1][2],1000);self.assertEqual(self.provider.calls[-1][3],self.provider.calls[-2][3])
 def test_live_credentials_rejected(self):
  for args in [('live_client','test_secret'),('test_client','live_secret')]:
   with self.assertRaises(RuntimeError):TossSandbox(*args)

class HttpTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=AccountStore(self.temp.name);self.server=create_server(self.store,('127.0.0.1',0));self.port=self.server.server_port;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.cookies=http.cookiejar.CookieJar();self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def request(self,path,method='GET',body=None,csrf=None,origin='http://127.0.0.1:8766'):
  headers={'Origin':origin}
  if csrf:headers['X-CSRF-Token']=csrf
  if body is not None:headers['Content-Type']='application/json'
  req=urllib.request.Request(f'http://127.0.0.1:{self.port}'+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  try:
   with self.client.open(req) as response:return response.status,response.headers,response.read()
  except urllib.error.HTTPError as e:
   with e:return e.code,e.headers,e.read()
 def test_browser_cookie_csrf_origin_roundtrip(self):
  status,headers,body=self.request('/api/register','POST',{'email':'http@example.invalid','password':'Synthetic-password'});self.assertEqual(status,200);user=json.loads(body)
  self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie']);self.assertEqual(headers['Access-Control-Allow-Credentials'],'true')
  self.assertEqual(self.request('/api/files','POST',{'name':'test.pdf','pdf':base64.b64encode(PDF).decode()})[0],403)
  status,_,body=self.request('/api/files','POST',{'name':'test.pdf','pdf':base64.b64encode(PDF).decode()},user['csrf']);self.assertEqual(status,200);item=json.loads(body)
  self.assertEqual(self.request('/api/files/'+item['id'])[2],PDF);self.assertEqual(self.request('/api/me',origin='https://untrusted.invalid')[0],403)
  self.assertEqual(self.request('/api/logout','POST',{},user['csrf'])[0],200);self.assertEqual(self.request('/api/me')[0],401)
 def test_server_price_and_duplicate_payment(self):
  _,_,body=self.request('/api/register','POST',{'email':'billing@example.invalid','password':'Synthetic-password'});user=json.loads(body)
  status,_,body=self.request('/api/orders','POST',{'sku':'storage-test','provider':'demo','amount':1},user['csrf']);self.assertEqual(status,200);order=json.loads(body);self.assertEqual(order['amount'],1000)
  for _ in range(2):self.assertEqual(self.request('/api/payments/demo','POST',{'orderId':order['id'],'outcome':'DONE'},user['csrf'])[0],200)
  self.assertEqual(json.loads(self.request('/api/me')[2])['maxFiles'],50)

if __name__=='__main__':unittest.main(verbosity=2)
