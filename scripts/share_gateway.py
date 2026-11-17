"""Password-gated static site and fixed loopback API proxy for a teacher demo."""
import hashlib
import hmac
import html
import http.client
import json
import mimetypes
import secrets
import threading
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

PDF_OPERATIONS={'protect','unlock','compress','word','powerpoint','repair','inspect','edit','redact','translate','office','pdfa','text-lines','replace-text','sign','verify-signatures','paragraphs','reflow','html','summarize','summary-pdf','workflow'}
ACCOUNT_ORIGIN='https://pdf-share.internal'
LIMIT=36*1024*1024
COOKIE='pdf_share_gate'

class ShareServer(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,root,password,account_port,address=('127.0.0.1',8770),pdf_port=8767):
  self.root=Path(root).resolve();self.password_hash=hashlib.sha256(password.encode()).digest();self.secret=secrets.token_bytes(32)
  self.public_origin='';self.run_id=secrets.token_hex(16);self.account_port=account_port;self.pdf_port=pdf_port
  self.attempts={};self.lock=threading.Lock();self.slots=threading.BoundedSemaphore(2)
  super().__init__(address,ShareHandler)
 def session(self):
  body=str(int(time.time()))+'.'+secrets.token_hex(16);return body+'.'+hmac.new(self.secret,body.encode(),'sha256').hexdigest()
 def valid_session(self,token):
  try:
   issued,nonce,signature=token.split('.');age=time.time()-int(issued)
   return 0<=age<28800 and len(nonce)==32 and hmac.compare_digest(signature,hmac.new(self.secret,(issued+'.'+nonce).encode(),'sha256').hexdigest())
  except (ValueError,TypeError):return False

class ShareHandler(BaseHTTPRequestHandler):
 server_version='PDFShare/1'
 def setup(self):super().setup();self.connection.settimeout(30)
 def log_message(self,*args):pass
 def send(self,status,body=b'',kind='text/plain; charset=utf-8',headers=()):
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
  for k,v in [('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','same-origin'),('X-Frame-Options','SAMEORIGIN'),*headers]:self.send_header(k,v)
  self.end_headers()
  if self.command!='HEAD':
   try:self.wfile.write(body)
   except (BrokenPipeError,ConnectionResetError):pass
 def fail(self,status,message):self.send(status,json.dumps({'error':message},ensure_ascii=False).encode(),'application/json; charset=utf-8')
 def host_allowed(self):
  host=self.headers.get('Host','');expected=urllib.parse.urlsplit(self.server.public_origin).netloc
  return host in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'} or bool(expected and host==expected)
 def authenticated(self):
  jar=SimpleCookie()
  try:jar.load(self.headers.get('Cookie',''));return COOKIE in jar and self.server.valid_session(jar[COOKIE].value)
  except Exception:return False
 def origin_allowed(self):
  origin=self.headers.get('Origin')
  return bool(self.server.public_origin and origin==self.server.public_origin) or origin==f'http://127.0.0.1:{self.server.server_port}'
 def read_body(self,limit=LIMIT):
  if self.headers.get('Transfer-Encoding'):raise ValueError('Chunked requests are not supported')
  length=int(self.headers.get('Content-Length','0'))
  if not 0<length<=limit:raise ValueError('Request exceeds the supported file size')
  data=self.rfile.read(length)
  if len(data)!=length:raise ValueError('Incomplete request')
  return data
 def gate(self,message=''):
  target=urllib.parse.urlsplit(self.path).path
  if not target.startswith('/') or target.startswith('//'):target='/'
  body=('''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PDF 도구 공유</title><style>body{font-family:system-ui,sans-serif;background:#f4f4fa;color:#26344a;margin:0;padding:24px}main{max-width:460px;margin:10vh auto;background:white;padding:32px;border-radius:16px;box-shadow:0 6px 30px #0001}input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:12px;font:inherit;border-radius:8px;border:1px solid #bbb}button{background:#ed2929;color:white;border:0;cursor:pointer}p{line-height:1.7}.error{color:#b31313}</style><main><h1>PDF 도구 공유</h1><p>전달받은 공유 암호를 입력하세요.</p><form method="post" action="/share/login"><label for="code">공유 암호</label><input id="code" name="code" type="password" required autocomplete="off"><input type="hidden" name="next" value="'''+html.escape(target,quote=True)+'''"><button>PDF 도구 열기</button></form><p class="error">'''+html.escape(message)+'''</p><p>일부 변환·편집·AI 기능은 파일을 HTTPS로 운영자의 PC에 보내 처리합니다. 보관함은 공유 전용입니다. 수업 시험용 문서로 이용해 주세요.</p></main></html>''').encode()
  self.send(200,body,'text/html; charset=utf-8', [('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")])
 def do_HEAD(self):self.dispatch()
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def do_DELETE(self):self.dispatch()
 def do_OPTIONS(self):self.fail(403,'Cross-origin access is not enabled')
 def dispatch(self):
  if not self.host_allowed():self.fail(403,'허용되지 않은 주소입니다.');return
  path=urllib.parse.urlsplit(self.path).path
  if path=='/share/health' and self.command in {'GET','HEAD'}:
   self.send(200,json.dumps({'service':'local-pdf-share','runId':self.server.run_id}).encode(),'application/json');return
  if self.command not in {'GET','HEAD'} and not self.origin_allowed():self.fail(403,'허용되지 않은 출처입니다.');return
  if path=='/share/login' and self.command=='POST':
   ip=self.headers.get('CF-Connecting-IP',self.client_address[0])[:80]
   with self.server.lock:
    now=time.monotonic();self.server.attempts={k:[x for x in v if now-x<600] for k,v in self.server.attempts.items() if v and now-v[-1]<600}
    if len(self.server.attempts)>2048 or len(self.server.attempts.get(ip,[]))>=24:self.fail(429,'잠시 후 다시 시도하세요.');return
    self.server.attempts.setdefault(ip,[]).append(now)
   try:
    payload=urllib.parse.parse_qs(self.read_body(2048).decode());code=payload.get('code',[''])[0]
    if not hmac.compare_digest(hashlib.sha256(code.encode()).digest(),self.server.password_hash):self.gate('공유 암호를 확인하세요.');return
    target=payload.get('next',['/'])[0]
    if not target.startswith('/') or target.startswith('//') or '\\' in target or any(ord(c)<32 for c in target):target='/'
    secure='; Secure' if self.server.public_origin else ''
    self.send(303,headers=[('Location',target),('Set-Cookie',f'{COOKIE}={self.server.session()}; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800'+secure)])
   except (ValueError,UnicodeError):self.fail(400,'요청 형식을 확인하세요.')
   return
  if not self.authenticated():
   if self.command in {'GET','HEAD'} and (path.endswith('/') or path.endswith('.html')):self.gate()
   else:self.fail(401,'공유 암호를 먼저 입력하세요.')
   return
  if path.startswith('/pdf-api/') or path.startswith('/account-api/'):
   self.proxy(path);return
  if self.command not in {'GET','HEAD'}:self.fail(405,'지원하지 않는 요청입니다.');return
  decoded=urllib.parse.unquote(path)
  if '\\' in decoded or any(p.startswith('.') for p in decoded.split('/')):self.fail(404,'파일을 찾을 수 없습니다.');return
  file=(self.server.root/decoded.lstrip('/')).resolve()
  if not file.is_relative_to(self.server.root):self.fail(404,'파일을 찾을 수 없습니다.');return
  if file.is_dir():file=file/'index.html'
  if not file.is_file():self.fail(404,'파일을 찾을 수 없습니다.');return
  kind=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
  if file.suffix=='.wasm':kind='application/wasm'
  self.send(200,file.read_bytes(),kind)
 def proxy(self,path):
  is_pdf=path.startswith('/pdf-api/');suffix=path.split('/',2)[2];upstream='/'+suffix
  if is_pdf and (self.command!='POST' or suffix not in {'api/pdf/'+op for op in PDF_OPERATIONS}):self.fail(404,'경로를 찾을 수 없습니다.');return
  if not is_pdf and not (suffix in {'api/config','api/register','api/login','api/me','api/logout','api/files','api/orders','api/payments/demo'} or suffix.startswith('api/files/') or suffix.startswith('api/orders/')):self.fail(404,'경로를 찾을 수 없습니다.');return
  if not self.server.slots.acquire(False):self.fail(429,'다른 파일을 처리 중입니다. 잠시 후 다시 시도하세요.');return
  conn=None
  try:
   data=self.read_body() if self.command=='POST' else None
   headers={'Origin':'http://127.0.0.1:8766' if is_pdf else ACCOUNT_ORIGIN}
   for k in ['Content-Type','Cookie','X-CSRF-Token']:
    if self.headers.get(k):headers[k]=self.headers[k]
   conn=http.client.HTTPConnection('127.0.0.1',self.server.pdf_port if is_pdf else self.server.account_port,timeout=620)
   conn.request(self.command,upstream,body=data,headers=headers);response=conn.getresponse();body=response.read(100*1024*1024+1)
   if len(body)>100*1024*1024:raise ValueError('Result too large')
   forwarded=[(k,v) for k,v in response.getheaders() if k.lower() in {'set-cookie','content-disposition','x-conversion-mode','x-layout-result','x-html-blocked'}]
   self.send(response.status,body,response.getheader('Content-Type','application/octet-stream'),forwarded)
  except (ValueError,TimeoutError):self.fail(400,'파일 크기·형식을 확인하거나 잠시 후 다시 시도하세요.')
  except (OSError,http.client.HTTPException):self.fail(502,'운영자 PC의 문서 서비스에 연결하지 못했습니다.')
  finally:
   if conn:conn.close()
   self.server.slots.release()
