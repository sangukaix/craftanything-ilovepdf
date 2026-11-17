import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import runtime_config

class Tests(unittest.TestCase):
 def test_default_preserves_existing_local_model(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(runtime_config,'ROOT',Path(folder)),patch.dict('os.environ',{},clear=True):
   self.assertEqual(runtime_config.ai_settings(),('http://127.0.0.1:8080/v1','qwen3.8-flash-next-iq2_xs'))
 def test_portable_ollama_config(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(runtime_config,'ROOT',Path(folder)),patch.dict('os.environ',{},clear=True):
   path=Path(folder)/'.local-data';path.mkdir();(path/'runtime.json').write_text(json.dumps({'ai':{'provider':'ollama','baseUrl':'http://127.0.0.1:11435/v1','model':'pdf-qwen3.5-4b-32k'}}))
   self.assertEqual(runtime_config.ai_settings(),('http://127.0.0.1:11435/v1','pdf-qwen3.5-4b-32k'))
 def test_remote_and_embedded_credentials_rejected(self):
  for value in ['https://api.example.invalid/v1','http://user:password@127.0.0.1:8080/v1','file:///private']:
   with patch.object(runtime_config,'load_runtime',return_value={}),patch.dict('os.environ',{'PDF_AI_BASE_URL':value}),self.assertRaises(ValueError):runtime_config.ai_settings()
 def test_disabled_ai_does_not_fall_back_to_unrelated_server(self):
  with patch.object(runtime_config,'load_runtime',return_value={'ai':{'provider':'none'}}),self.assertRaisesRegex(ValueError,'disabled'):runtime_config.ai_settings()

if __name__=='__main__':unittest.main()
