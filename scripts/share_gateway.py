"""Public static project and fixed loopback API proxy for a teacher demo."""
import http.client
import json
import mimetypes
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

PDF_OPERATIONS={'protect','unlock','compress','word','powerpoint','repair','inspect','edit','redact','translate','office','pdfa','text-lines','replace-text','sign','verify-signatures','paragraphs','reflow','html','summarize','summary-pdf','workflow'}
ACCOUNT_ORIGIN='https://pdf-share.internal'
LIMIT=36*1024*1024

class ShareServer(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,root,account_port,address=('127.0.0.1',8770),pdf_port=8767):
  self.root=Path(root).resolve()
  self.public_origin='';self.run_id=secrets.token_hex(16);self.account_port=account_port;self.pdf_port=pdf_port
  self.slots=threading.BoundedSemaphore(2)
  super().__init__(address,ShareHandler)

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
