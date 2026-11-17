"""Loopback account API, encrypted per-user vault, explicitly simulated billing."""
import base64
import collections
import hmac
import json
import os
import threading
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from account_store import AccountStore,AccountError,TossSandbox,MAX_FILE

ROOT=Path(__file__).resolve().parents[1]
ORIGIN='http://127.0.0.1:8766'
SLOTS=threading.BoundedSemaphore(4)

def create_server(store,address=('127.0.0.1',8768),origin=ORIGIN):
 attempts=collections.defaultdict(list);lock=threading.Lock()
 class Handler(BaseHTTPRequestHandler):
  server_version='LocalVault/1'
  def log_message(self,*args):pass
  def response(self,status,data,cookie=None,filename=None):
   body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
   self.send_response(status);self.send_header('Content-Type','application/pdf' if filename else 'application/json; charset=utf-8')
   self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
   if self.headers.get('Origin')==origin:self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Vary','Origin')
   if cookie:self.send_header('Set-Cookie',cookie)
   if filename:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(filename));self.send_header('Access-Control-Expose-Headers','Content-Disposition')
   self.end_headers();self.wfile.write(body)
  def token(self):
   cookie=SimpleCookie()
   try:cookie.load(self.headers.get('Cookie',''))
   except Exception:return ''
   return cookie['pdf_session'].value if 'pdf_session' in cookie else ''
  def cookie(self,token):return f'pdf_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={28800 if token else 0}'+('; Secure' if origin.startswith('https://') else '')
  def guard(self):
   if self.headers.get('Host') not in {f'{address[0]}:{self.server.server_port}',f'localhost:{self.server.server_port}'}:raise AccountError('허용되지 않은 호스트입니다.',403)
   incoming=self.headers.get('Origin')
   if incoming is not None and incoming!=origin:raise AccountError('허용되지 않은 출처입니다.',403)
  def do_OPTIONS(self):
   try:self.guard()
   except AccountError as e:self.response(e.status,{'error':str(e)});return
   self.send_response(204);self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Access-Control-Allow-Methods','GET,POST,DELETE,OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type,X-CSRF-Token');self.send_header('Content-Length','0');self.end_headers()
  def do_GET(self):self.dispatch('GET')
  def do_POST(self):self.dispatch('POST')
  def do_DELETE(self):self.dispatch('DELETE')
  def dispatch(self,method):
   if not SLOTS.acquire(False):self.response(429,{'error':'요청이 많습니다. 잠시 후 다시 시도하세요.'});return
   try:
    self.guard();path=urllib.parse.urlsplit(self.path).path;payload={}
    if method=='POST':
     length=int(self.headers.get('Content-Length','0'))
     if not 0<length<=MAX_FILE*4//3+8192:raise AccountError('요청 크기를 확인하세요.',413)
     if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise AccountError('JSON 요청이 필요합니다.',415)
     payload=json.loads(self.rfile.read(length))
     if not isinstance(payload,dict):raise AccountError('요청 형식을 확인하세요.')
    if method=='GET' and path=='/health':self.response(200,{'service':'local-pdf-account','mode':'test'});return
    if method=='GET' and path=='/api/config':self.response(200,store.config());return
    if method=='POST' and path in {'/api/register','/api/login'}:
     with lock:
      now=time.monotonic();key=(self.client_address[0],path);attempts[key]=[t for t in attempts[key] if now-t<600]
      if len(attempts[key])>=20:raise AccountError('잠시 후 다시 시도하세요.',429)
      attempts[key].append(now)
     token,user=(store.register if path.endswith('register') else store.login)(payload.get('email',''),payload.get('password',''))
     self.response(200,user,cookie=self.cookie(token));return
    if method=='POST' and path=='/api/webhook/toss':self.response(200,store.reconcile(payload.get('data',{}).get('paymentKey','')));return
    token=self.token();session=store.session(token);user=session['user_id']
    if method!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):raise AccountError('요청 인증이 만료되었습니다. 새로고침하세요.',403)
    if method=='GET' and path=='/api/me':result=store.me(token)
    elif method=='POST' and path=='/api/logout':store.logout(token);self.response(200,{'ok':True},cookie=self.cookie(''));return
    elif method=='GET' and path=='/api/files':result=store.list_files(user)
    elif method=='POST' and path=='/api/files':
     try:data=base64.b64decode(payload.get('pdf',''),validate=True)
     except Exception:raise AccountError('PDF 파일을 읽지 못했습니다.')
     result=store.upload(user,payload.get('name',''),data)
    elif path.startswith('/api/files/') and method in {'GET','DELETE'}:
     file_id=path.rsplit('/',1)[-1]
     if method=='GET':name,data=store.download(user,file_id);self.response(200,data,filename=name);return
     store.delete(user,file_id);result={'deleted':True}
    elif method=='GET' and path=='/api/orders':result=store.orders(user)
    elif method=='POST' and path=='/api/orders':result=store.create_order(user,payload.get('sku'),payload.get('provider'))
    elif method=='GET' and path.startswith('/api/orders/'):result=store.order(user,path.rsplit('/',1)[-1])
    elif method=='POST' and path=='/api/payments/demo':result=store.demo_result(user,payload.get('orderId'),payload.get('outcome'))
    elif method=='POST' and path=='/api/payments/confirm':result=store.confirm(user,payload.get('orderId'),payload.get('paymentKey'),payload.get('amount'))
    else:raise AccountError('경로를 찾을 수 없습니다.',404)
    self.response(200,result)
   except AccountError as error:self.response(error.status,{'error':str(error)})
   except (ValueError,TypeError,AttributeError,OverflowError):self.response(400,{'error':'요청 형식을 확인하세요.'})
   except Exception:self.response(500,{'error':'처리하지 못했습니다. 다시 시도하세요.'})
   finally:SLOTS.release()
 return ThreadingHTTPServer(address,Handler)

if __name__=='__main__':
 provider=TossSandbox(os.environ.get('PDF_TOSS_TEST_CLIENT_KEY',''),os.environ.get('PDF_TOSS_TEST_SECRET_KEY',''))
 store=AccountStore(ROOT/'.local-data/accounts',provider)
 web_origin=os.environ.get('PDF_WEB_ORIGIN',ORIGIN)
 if web_origin!=ORIGIN and not web_origin.startswith('https://'):raise RuntimeError('외부 연결은 HTTPS 출처를 명시하세요.')
 server=create_server(store,origin=web_origin);print('계정·보관함·모의 결제: http://127.0.0.1:8768 (실제 청구 없음)',flush=True);server.serve_forever()
