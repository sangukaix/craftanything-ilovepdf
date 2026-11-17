import io
import re
import unittest
from pathlib import Path
import pymupdf
from PIL import Image
from pdf_extra import ExtraInputError
from pdf_layout import get_paragraphs,reflow_paragraph

def fixture(count=2):
 doc=pymupdf.open();page=doc.new_page(width=595,height=842);page.insert_text((50,35),'FIXED HEADER',fontsize=14,fontname='hebo');page.insert_text((50,820),'FIXED FOOTER',fontsize=10)
 width=(495-(count-1)*24)/count
 for c in range(count):
  x=50+c*(width+24)
  for n,y in enumerate([100,220,600]):
   page.insert_textbox(pymupdf.Rect(x,y,x+width,y+70),f'COL{c}P{n} Original article body.\nSecond line preserves Times typeface.',fontsize=10,fontname='tiro')
 image=Image.new('RGB',(80,50),'#4d93cb');buffer=io.BytesIO();image.save(buffer,format='PNG');page.insert_image(pymupdf.Rect(50,350,50+width,440),stream=buffer.getvalue())
 # The table is drawn as individual connected edges, not one drawing object.
 x=50+width+24 if count==2 else 50+2*(width+24)
 for y in [350,385,420]:page.draw_line((x,y),(x+width,y))
 for xx in [x,x+width/2,x+width]:page.draw_line((xx,350),(xx,420))
 page.insert_text((x+5,372),'TABLE KEEP',fontsize=8);page.insert_text((x+5,407),'VALUE 2718',fontsize=8)
 data=doc.tobytes();doc.close();return data

def request(source,count=2,repeats=100):
 block=next(p for p in get_paragraphs(source,1)['paragraphs'] if p['text'].startswith('COL0P0'))
 return {'page':1,'id':block['id'],'original':block['text'],'text':'Expanded item. '*repeats,'fontMode':'strict','leading':1.4,'alignment':'left','flowMode':'columns','columns':count,'gutter':24,'margin':50,'bodyTop':80,'bodyBottom':782}

class ColumnTests(unittest.TestCase):
 def test_two_and_three_column_flow_preserves_content_and_graphics(self):
  for count in [2,3]:
   with self.subTest(count=count):
    source=fixture(count);output,report=reflow_paragraph(source,request(source,count,260))
    with pymupdf.open(stream=source,filetype='pdf') as before,pymupdf.open(stream=output,filetype='pdf') as after:
     text=re.sub(r'\s+',' ',' '.join(p.get_text() for p in after));self.assertEqual(text.count('Expanded item.'),260)
     for c in range(count):
      for n in range(3):self.assertEqual(text.count(f'COL{c}P{n}'),0 if c==n==0 else 1)
     for fixed in ['FIXED HEADER','FIXED FOOTER','TABLE KEEP','VALUE 2718']:self.assertEqual(text.count(fixed),1)
     self.assertEqual(len(before[0].get_images()),len(after[0].get_images()));self.assertEqual(len(before[0].get_drawings()),len(after[0].get_drawings()))
     self.assertGreater(len(after),1);self.assertEqual(report['fallbackStyles'],0);self.assertIn('Times-Roman',report['fonts'])
     # Image and vector table pixels must remain identical.
     col_width=(495-(count-1)*24)/count;table_x=50+(count-1)*(col_width+24)
     for rect in [pymupdf.Rect(50,350,50+col_width,440),pymupdf.Rect(table_x,350,table_x+col_width,420),pymupdf.Rect(40,5,555,45),pymupdf.Rect(40,800,555,835)]:
      self.assertEqual(before[0].get_pixmap(clip=rect).samples,after[0].get_pixmap(clip=rect).samples)
     for page in after:
      for b in page.get_text('dict')['blocks']:
       for line in b.get('lines',[]):
        for span in line['spans']:
         rect=pymupdf.Rect(span['bbox']);self.assertTrue(page.rect.contains(rect))
 def test_fixed_table_selection_refused(self):
  source=fixture();block=next(p for p in get_paragraphs(source,1)['paragraphs'] if p['text'].startswith('TABLE'))
  with self.assertRaises(ExtraInputError):reflow_paragraph(source,{**request(source),'id':block['id'],'original':block['text']})
 def test_existing_second_page_heading_link_and_bold_font_preserved(self):
  source=fixture();doc=pymupdf.open(stream=source,filetype='pdf');page=doc.new_page(width=595,height=842)
  page.insert_text((50,130),'WIDE SECTION HEADING ACROSS BOTH COLUMNS',fontsize=17,fontname='hebo')
  page.insert_text((50,230),'SECOND PAGE BOLD BODY',fontsize=11,fontname='tibo')
  page.insert_text((310,510),'LINK KEEP',fontsize=11);page.insert_link({'kind':pymupdf.LINK_URI,'from':pymupdf.Rect(307,495,410,515),'uri':'https://example.invalid/'})
  source=doc.tobytes();doc.close();output,report=reflow_paragraph(source,request(source,2,260))
  with pymupdf.open(stream=output,filetype='pdf') as result:
   text=' '.join(p.get_text() for p in result)
   for phrase in ['SECOND PAGE BOLD BODY','WIDE SECTION HEADING ACROSS BOTH COLUMNS','LINK KEEP']:self.assertEqual(text.count(phrase),1)
   self.assertEqual(len(result[1].get_links()),1);self.assertEqual(result[1].get_links()[0]['uri'],'https://example.invalid/');self.assertIn('Times-Bold',report['fonts'])
 def test_invalid_geometry_and_stale_source_refused(self):
  source=fixture()
  for change in [{'columns':4},{'gutter':-1},{'bodyBottom':900},{'original':'stale'},{'margin':float('nan')}]:
   with self.assertRaises(ExtraInputError):reflow_paragraph(source,{**request(source),**change})

if __name__=='__main__':unittest.main(verbosity=2)
