import io
import re
import unittest
import os
from pathlib import Path
import pymupdf
from pdf_extra import FONT,ExtraInputError
from pdf_layout import get_paragraphs,reflow_paragraph
from pdf_advanced import text_lines,replace_text
from pdf_web import html_to_pdf,summarize_pdf,public_url
from pdf_workflows import run_workflow
from pdf_service import process_pdf
from pdf_advanced import pdfa_convert

def paragraph_source(embedded=False,mixed=False):
 doc=pymupdf.open();page=doc.new_page(width=595,height=842)
 font='tiro'
 if embedded:
  font='originalFont';page.insert_font(fontname=font,fontfile=str(FONT))
 page.insert_text((50,80),'Original paragraph first line.',fontsize=12,fontname=font,color=(.2,.1,.5))
 page.insert_text((50,98),'Second line of the paragraph.',fontsize=12,fontname='tibi' if mixed else font,color=(.2,.1,.5))
 page.insert_text((50,400),'KEEP THIS BLOCK',fontsize=14)
 data=doc.tobytes();doc.close();return data

def paragraph_payload(source,text='A much longer paragraph that wraps across several lines with the same original typeface and preserves the separate block.'):
 block=get_paragraphs(source,1)['paragraphs'][0]
 return {'page':1,'id':block['id'],'original':block['text'],'text':text,'x':50,'y':50,'width':180,'height':200,'fontMode':'strict','leading':1.4,'alignment':'left'}

class Tests(unittest.TestCase):
 def test_original_base14_font_preserved_on_line_edit(self):
  source=paragraph_source();line=text_lines(source,1)['lines'][0]
  output=replace_text(source,{'operations':[{'page':1,'id':line['id'],'original':line['text'],'text':'Edited sentence.'}],'fontMode':'strict'})
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   spans=[s for b in doc[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
   span=next(s for s in spans if 'Edited sentence' in s['text']);self.assertEqual(span['font'],'Times-Roman')

 def test_paragraph_wrap_and_untouched_block(self):
  source=paragraph_source();output,report=reflow_paragraph(source,paragraph_payload(source))
  self.assertGreater(report['lines'],2);self.assertEqual(report['fallbackStyles'],0)
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   text=doc[0].get_text();self.assertNotIn('Original paragraph',text);self.assertIn('KEEP THIS BLOCK',text)
   self.assertIn('Times-Roman',report['fonts'])

 def test_embedded_font_and_mixed_styles(self):
  for embedded,mixed in [(True,False),(False,True)]:
   with self.subTest(embedded=embedded,mixed=mixed):
    source=paragraph_source(embedded,mixed);payload=paragraph_payload(source)
    payload['text']=payload['original']+' Extra text.'
    output,report=reflow_paragraph(source,payload);self.assertEqual(report['fallbackStyles'],0)
    self.assertGreater(len(output),1000)
    if mixed:self.assertIn('Times-BoldItalic',report['fonts'])

 def test_overflow_and_collision_rejected(self):
  source=paragraph_source()
  for edit in [{'height':8},{'y':380,'height':80}]:
   with self.assertRaises(ExtraInputError):reflow_paragraph(source,{**paragraph_payload(source),**edit})

 def test_unsupported_character_strict_rejected_and_auto_fallback(self):
  source=paragraph_source();payload=paragraph_payload(source,'Latin 한국어 문단으로 변경합니다.')
  with self.assertRaises(ExtraInputError):reflow_paragraph(source,payload)
  output,report=reflow_paragraph(source,{**payload,'fontMode':'auto'});self.assertGreater(report['fallbackStyles'],0)
  self.assertIn('Times-Roman',report['fonts']);self.assertIn('NotoSansKR-Regular',report['fonts'])
  with pymupdf.open(stream=output,filetype='pdf') as doc:self.assertIn('한국어',doc[0].get_text())

 def test_html_korean_css_javascript_disabled(self):
  html='<html><body><h1>HTML 한국어 시험</h1><p>Invoice 12345</p><script>document.body.innerHTML="UNSAFE SCRIPT EXECUTED"</script><img src="http://127.0.0.1:8767/health"></body></html>'
  output,report=html_to_pdf({'html':html})
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   self.assertIn('HTML 한국어 시험',doc[0].get_text());self.assertIn('12345',doc[0].get_text());self.assertNotIn('UNSAFE SCRIPT EXECUTED',doc[0].get_text())
  self.assertGreater(report['blockedRequests'],0)

 def test_private_urls_rejected(self):
  for url in ['file:///C:/Windows/win.ini','http://127.0.0.1:8767/health','http://192.168.1.1/','https://user:password@example.com/','http://[::1]/']:
   self.assertFalse(public_url(url))
   with self.assertRaises(ExtraInputError):html_to_pdf({'url':url})

 def test_dynamic_html_opt_in(self):
  html='<html><body><script>document.body.innerHTML="<h1>Dynamic invoice 54321</h1>";fetch("http://127.0.0.1:8767/health").catch(()=>{});</script></body></html>'
  output,report=html_to_pdf({'html':html,'javascript':True})
  with pymupdf.open(stream=output,filetype='pdf') as doc:self.assertIn('Dynamic invoice 54321',doc[0].get_text())
  self.assertTrue(report['javascript']);self.assertGreater(report['blockedRequests'],0)

 @unittest.skipIf(os.environ.get('PDF_SKIP_AI_TESTS')=='1','Local AI explicitly disabled for this run')
 def test_actual_local_model_summary(self):
  doc=pymupdf.open();page=doc.new_page();page.insert_text((50,80),'Project budget is 180 units. The deadline is November 17, 2026.');source=doc.tobytes();doc.close()
  result=summarize_pdf(source,{'language':'en','length':'short'})
  self.assertIn('180',result['summary']);self.assertTrue(result['summary'].strip());self.assertEqual(result['pages'],1)

 def test_paragraph_auto_flow_to_new_pages_without_text_loss(self):
  source=paragraph_source();text='Expanded body material. '*240;payload=paragraph_payload(source,text)
  output,report=reflow_paragraph(source,{**payload,'flow':True,'y':50,'height':160})
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   self.assertGreater(len(doc),1);combined=re.sub(r'\s+',' ',' '.join(p.get_text() for p in doc))
   self.assertEqual(combined.count('Expanded body material.'),240);self.assertEqual(combined.count('KEEP THIS BLOCK'),1)
   self.assertNotIn('Original paragraph',combined);self.assertEqual(report['pages'],len(doc));self.assertEqual(report['fallbackStyles'],0)

 def test_auto_flow_existing_next_page_and_complex_rejection(self):
  source=paragraph_source();doc=pymupdf.open(stream=source,filetype='pdf');doc.new_page(width=595,height=842).insert_text((50,80),'SECOND PAGE UNIQUE',fontsize=12);source=doc.tobytes();doc.close()
  output,report=reflow_paragraph(source,{**paragraph_payload(source,'Short new body.'),'flow':True,'height':600})
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   self.assertEqual(len(doc),1);text=doc[0].get_text();self.assertIn('SECOND PAGE UNIQUE',text);self.assertIn('KEEP THIS BLOCK',text)
  doc=pymupdf.open(stream=source,filetype='pdf');doc[0].draw_rect(pymupdf.Rect(10,10,20,20));complex_source=doc.tobytes();doc.close()
  with self.assertRaises(ExtraInputError):reflow_paragraph(complex_source,{**paragraph_payload(complex_source),'flow':True})

 def test_workflow_chains_rotation_watermark_number_compression(self):
  source=paragraph_source();steps=[{'operation':'rotate','angle':90},{'operation':'watermark','text':'검증 워크플로'},{'operation':'number'},{'operation':'compress'}]
  output=run_workflow(source,steps,process_pdf,pdfa_convert)
  with pymupdf.open(stream=output,filetype='pdf') as doc:
   self.assertEqual(doc[0].rotation,90);self.assertIn('KEEP THIS BLOCK',doc[0].get_text());self.assertIn('검증',doc[0].get_text())

 def test_workflow_terminal_steps_and_protection(self):
  source=paragraph_source()
  output=run_workflow(source,[{'operation':'number'},{'operation':'protect','password':'test-only'}],process_pdf,pdfa_convert)
  with pymupdf.open(stream=output,filetype='pdf') as doc:self.assertTrue(doc.is_encrypted);self.assertTrue(doc.authenticate('test-only'))
  for steps in [[{'operation':'protect','password':'test-only'},{'operation':'number'}],[{'operation':'pdfa'},{'operation':'protect'}]]:
   with self.assertRaises(ExtraInputError):run_workflow(source,steps,process_pdf,pdfa_convert)

if __name__=='__main__':unittest.main()
