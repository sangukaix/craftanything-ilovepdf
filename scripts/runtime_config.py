"""Machine-local runtime selection; no credentials or cloud inference."""
import json
import os
import urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load_runtime():
 path=ROOT/'.local-data/runtime.json'
 if not path.exists():return {}
 value=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(value,dict):raise ValueError('runtime.json must be an object')
 return value

def ai_settings():
 value=load_runtime().get('ai',{})
 if value.get('provider')=='none':raise ValueError('Local AI is disabled. Run setup.cmd -AiEngine Ollama or configure a local model first.')
 base=os.environ.get('PDF_AI_BASE_URL',value.get('baseUrl','http://127.0.0.1:8080/v1')).rstrip('/')
 parsed=urllib.parse.urlsplit(base)
 if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'} or parsed.username or parsed.password:raise ValueError('AI endpoint must be a loopback HTTP server without embedded credentials')
 model=os.environ.get('PDF_AI_MODEL',value.get('model','qwen3.8-flash-next-iq2_xs'))
 if not isinstance(model,str) or not model or len(model)>200:raise ValueError('Invalid local AI model name')
 return base,model
