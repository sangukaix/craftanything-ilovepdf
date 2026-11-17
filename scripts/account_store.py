"""Isolated account vault and payment sandbox. No live payment mode."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAX_FILE=25*1024*1024
DAY=86400
CATALOG={'storage-test':{'name':'개인 보관함 확장 · 30일 모의 이용권','amount':1000,'currency':'KRW','days':30}}

class AccountError(ValueError):
 def __init__(self,message,status=400):super().__init__(message);self.status=status

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

class TossSandbox:
 """V2 widget checkout confirmation; TEST credentials only, never read .env."""
 def __init__(self,client_key='',secret_key=''):
  self.client_key=client_key;self.secret_key=secret_key
  if client_key and not client_key.startswith('test_'):raise RuntimeError('테스트 클라이언트 키만 허용합니다.')
  if secret_key and not secret_key.startswith('test_'):raise RuntimeError('테스트 시크릿 키만 허용합니다.')
 @property
 def ready(self):return bool(self.client_key and self.secret_key)
 def request(self,path,payload=None,idempotency=None):
  if not self.ready:raise AccountError('Toss 테스트 키가 아직 연결되지 않았습니다.',503)
  headers={'Authorization':'Basic '+base64.b64encode((self.secret_key+':').encode()).decode(),'Content-Type':'application/json'}
  if idempotency:headers['Idempotency-Key']=idempotency
  request=urllib.request.Request('https://api.tosspayments.com/v1/payments/'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
  except Exception:raise AccountError('결제사의 테스트 응답을 확인하지 못했습니다. 주문 내역에서 다시 확인하세요.',502)
 def confirm(self,key,order_id,amount,idempotency):
  return self.request('confirm',{'paymentKey':key,'orderId':order_id,'amount':amount},idempotency)
 def retrieve(self,key):
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',key):raise AccountError('결제 식별자를 확인하세요.')
  return self.request(key)

class AccountStore:
 def __init__(self,directory,provider=None):
  self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
  self.db_path=self.directory/'accounts.sqlite3';key_path=self.directory/'vault.key'
  try:
   with key_path.open('xb') as f:f.write(AESGCM.generate_key(bit_length=256))
  except FileExistsError:pass
  self.cipher=AESGCM(key_path.read_bytes());self.provider=provider or TossSandbox()
  with self.db() as db:
   db.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,salt BLOB NOT NULL,password BLOB NOT NULL,created INTEGER NOT NULL,paid_until INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,csrf TEXT NOT NULL,expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,name TEXT NOT NULL,size INTEGER NOT NULL,created INTEGER NOT NULL,body BLOB NOT NULL);
    CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,provider TEXT NOT NULL,sku TEXT NOT NULL,amount INTEGER NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,payment_key TEXT UNIQUE,applied INTEGER NOT NULL DEFAULT 0);
   ''')
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row
  try:
   with db:yield db
  finally:db.close()
 def config(self):return {'mode':'test','providers':['demo']+(['toss'] if self.provider.ready else []),'tossClientKey':self.provider.client_key if self.provider.ready else '', 'catalog':CATALOG,'deployed':False}
 def session(self,token):
  with self.db() as db:
   row=db.execute('SELECT s.*,u.email,u.paid_until FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(digest(token),int(time.time()))).fetchone()
  if not row:raise AccountError('로그인 후 이용하세요.',401)
  return dict(row)
 def begin_session(self,user_id):
  token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
  with self.db() as db:
   db.execute('DELETE FROM sessions WHERE expires<?',(int(time.time()),))
   db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),user_id,csrf,int(time.time())+8*3600))
  return token,self.me(token)
 def register(self,email,password):
  email=str(email).strip().lower()
  if not re.fullmatch(r'[^\s@]{1,64}@[^\s@]{1,189}\.[^\s@]{2,}',email) or len(email)>254:raise AccountError('이메일 형식을 확인하세요.')
  if not isinstance(password,str) or not 10<=len(password)<=128:raise AccountError('비밀번호는 10~128자로 입력하세요.')
  salt=secrets.token_bytes(16);hashed=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1)
  user_id=str(uuid.uuid4())
  try:
   with self.db() as db:db.execute('INSERT INTO users(id,email,salt,password,created) VALUES(?,?,?,?,?)',(user_id,email,salt,hashed,int(time.time())))
  except sqlite3.IntegrityError:raise AccountError('이 이메일로 가입할 수 없습니다. 로그인해 주세요.',409)
  return self.begin_session(user_id)
 def login(self,email,password):
  if not isinstance(password,str) or len(password)>128:raise AccountError('이메일 또는 비밀번호를 확인하세요.',401)
  with self.db() as db:row=db.execute('SELECT * FROM users WHERE email=?',(str(email).strip().lower(),)).fetchone()
  hashed=hashlib.scrypt(password.encode(),salt=bytes(row['salt']) if row else b'0'*16,n=16384,r=8,p=1)
  if not row or not hmac.compare_digest(hashed,bytes(row['password'])):raise AccountError('이메일 또는 비밀번호를 확인하세요.',401)
  return self.begin_session(row['id'])
 def logout(self,token):
  with self.db() as db:db.execute('DELETE FROM sessions WHERE token=?',(digest(token),))
 def me(self,token):
  session=self.session(token);paid=session['paid_until']>int(time.time());count,used=self.usage(session['user_id'])
  return {'id':session['user_id'],'email':session['email'],'csrf':session['csrf'],'paidUntil':session['paid_until'],'plan':'test-expanded' if paid else 'free','files':count,'bytes':used,'maxFiles':50 if paid else 5,'maxBytes':200*1024*1024 if paid else MAX_FILE,'emailVerified':False}
 def usage(self,user_id):
  with self.db() as db:return tuple(db.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM files WHERE user_id=?',(user_id,)).fetchone())
 def list_files(self,user):
  with self.db() as db:return [dict(r) for r in db.execute('SELECT id,name,size,created FROM files WHERE user_id=? ORDER BY created DESC,id',(user,))]
 def upload(self,user,name,data):
  if not isinstance(name,str) or not 1<=len(name)<=180 or any(ord(c)<32 for c in name) or any(c in name for c in '/\\'):raise AccountError('파일 이름을 확인하세요.')
  if not isinstance(data,bytes) or not data.startswith(b'%PDF-') or not 0<len(data)<=MAX_FILE:raise AccountError('25MB 이하 PDF만 보관할 수 있습니다.')
  # IDs, not filenames, address storage. AEAD binds every blob to its owner/id.
  file_id=str(uuid.uuid4());nonce=secrets.token_bytes(12);body=nonce+self.cipher.encrypt(nonce,data,(user+':'+file_id).encode())
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT paid_until FROM users WHERE id=?',(user,)).fetchone()
   if not row:raise AccountError('계정이 없습니다.',401)
   count,used=tuple(db.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM files WHERE user_id=?',(user,)).fetchone());paid=row['paid_until']>int(time.time())
   if count>=(50 if paid else 5) or used+len(data)>(200*1024*1024 if paid else MAX_FILE):raise AccountError('보관함 한도를 초과했습니다.',409)
   db.execute('INSERT INTO files VALUES(?,?,?,?,?,?)',(file_id,user,name,len(data),int(time.time()),body))
  return {'id':file_id,'name':name,'size':len(data)}
 def download(self,user,file_id):
  with self.db() as db:row=db.execute('SELECT * FROM files WHERE user_id=? AND id=?',(user,file_id)).fetchone()
  if not row:raise AccountError('파일을 찾을 수 없습니다.',404)
  body=bytes(row['body']);return row['name'],self.cipher.decrypt(body[:12],body[12:],(user+':'+file_id).encode())
 def delete(self,user,file_id):
  with self.db() as db:
   result=db.execute('DELETE FROM files WHERE user_id=? AND id=?',(user,file_id))
   if not result.rowcount:raise AccountError('파일을 찾을 수 없습니다.',404)
 def create_order(self,user,sku,provider):
  if sku not in CATALOG or provider not in self.config()['providers']:raise AccountError('테스트 상품·결제 방식을 확인하세요.')
  entry=CATALOG[sku];order_id='pdf_'+uuid.uuid4().hex
  with self.db() as db:db.execute('INSERT INTO orders(id,user_id,provider,sku,amount,currency,status,created) VALUES(?,?,?,?,?,?,?,?)',(order_id,user,provider,sku,entry['amount'],entry['currency'],'PENDING',int(time.time())))
  return self.order(user,order_id)
 def order(self,user,order_id):
  with self.db() as db:row=db.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,user)).fetchone()
  if not row:raise AccountError('주문을 찾을 수 없습니다.',404)
  result=dict(row);result['name']=CATALOG[row['sku']]['name'];result.pop('payment_key',None);return result
 def orders(self,user):
  with self.db() as db:ids=[r[0] for r in db.execute('SELECT id FROM orders WHERE user_id=? ORDER BY created DESC,id LIMIT 100',(user,))]
  return [self.order(user,i) for i in ids]
 def apply_paid(self,order,proof):
  if proof.get('orderId')!=order['id'] or type(proof.get('totalAmount')) is not int or proof['totalAmount']!=order['amount'] or proof.get('currency')!=order['currency'] or proof.get('status')!='DONE' or not isinstance(proof.get('paymentKey'),str) or not proof['paymentKey']:raise AccountError('결제 증빙의 주문·금액·통화·상태가 일치하지 않습니다.',409)
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');current=db.execute('SELECT * FROM orders WHERE id=?',(order['id'],)).fetchone()
   if current['applied']:
    if current['payment_key']!=proof['paymentKey']:raise AccountError('이미 다른 결제 증빙으로 처리된 주문입니다.',409)
    return
   if current['status']!='PENDING':raise AccountError('완료할 수 없는 주문 상태입니다.',409)
   try:db.execute('UPDATE orders SET status=?,payment_key=?,applied=1 WHERE id=?',('DONE',proof['paymentKey'],order['id']))
   except sqlite3.IntegrityError:raise AccountError('이미 처리된 결제 증빙입니다.',409)
   db.execute('UPDATE users SET paid_until=MAX(paid_until,?)+? WHERE id=?',(int(time.time()),CATALOG[order['sku']]['days']*DAY,order['user_id']))
 def demo_result(self,user,order_id,outcome):
  order=self.order(user,order_id)
  if order['provider']!='demo' or outcome not in {'DONE','FAILED','CANCELED'}:raise AccountError('모의 결제 요청을 확인하세요.')
  if outcome=='DONE':self.apply_paid(order,{'orderId':order_id,'totalAmount':order['amount'],'currency':order['currency'],'status':'DONE','paymentKey':'demo_'+order_id})
  else:
   with self.db() as db:
    result=db.execute('UPDATE orders SET status=? WHERE id=? AND status=?',(outcome,order_id,'PENDING'))
    if not result.rowcount and order['status']!=outcome:raise AccountError('이미 완료된 주문입니다.',409)
  return self.order(user,order_id)
 def confirm(self,user,order_id,payment_key,amount):
  order=self.order(user,order_id)
  if order['provider']!='toss' or type(amount) is not int or amount!=order['amount'] or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',str(payment_key)):raise AccountError('주문·테스트 금액을 확인하세요.',409)
  proof=self.provider.confirm(payment_key,order_id,order['amount'],str(uuid.UUID(order_id.removeprefix('pdf_'))))
  if proof.get('paymentKey')!=payment_key:raise AccountError('결제 식별자가 일치하지 않습니다.',409)
  self.apply_paid(order,proof);return self.order(user,order_id)
 def reconcile(self,payment_key):
  # Webhook payload alone never grants credit; verify through the provider API.
  proof=self.provider.retrieve(payment_key)
  with self.db() as db:row=db.execute('SELECT * FROM orders WHERE id=? AND provider=?',(proof.get('orderId'),'toss')).fetchone()
  if not row:raise AccountError('등록된 테스트 주문이 없습니다.',404)
  if proof.get('paymentKey')!=payment_key:raise AccountError('결제 식별자가 일치하지 않습니다.',409)
  self.apply_paid(dict(row),proof);return {'received':True}
