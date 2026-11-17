"""Local PDF font reuse and bounded paragraph reflow."""
import difflib
import hashlib
import math
import re
import pymupdf
from pdf_extra import FONT, ExtraInputError, open_pdf, rect_for

BASE14={
 "Helvetica":"helv","Helvetica-Bold":"hebo","Helvetica-Oblique":"heit","Helvetica-BoldOblique":"hebi",
 "Times-Roman":"tiro","Times-Bold":"tibo","Times-Italic":"tiit","Times-BoldItalic":"tibi",
 "Courier":"cour","Courier-Bold":"cobo","Courier-Oblique":"coit","Courier-BoldOblique":"cobi"}
def normalized(name):
 return re.sub(r"^[A-Z]{6}\+","",name).replace(" ","").replace("-","").replace("_","").lower()

class FontManager:
 def __init__(self,document,page):
  self.document=document;self.page=page;self.cache={};self.fallback=pymupdf.Font(fontfile=str(FONT));self.fallback_count=0;self.fallback_names=set()
  self.fallback_entry=(self.fallback,"noto_fallback",FONT.read_bytes(),"NotoSansKR-Regular")
 def original(self,name):
  if name in self.cache:return self.cache[name]
  clean=re.sub(r"^[A-Z]{6}\+","",name)
  if clean in BASE14:
   font=pymupdf.Font(fontname=BASE14[clean]);entry=(font,BASE14[clean],None,clean)
  else:
   match=next((f for f in self.page.get_fonts(full=True) if normalized(f[3])==normalized(name)),None)
   if not match:raise ExtraInputError("원래 글꼴 리소스를 찾을 수 없습니다.")
   try:
    _,extension,_,buffer=self.document.extract_font(match[0])
    if not buffer:raise ValueError()
    font=pymupdf.Font(fontbuffer=buffer);resource="kept_"+hashlib.sha256(buffer).hexdigest()[:12]
    entry=(font,resource,buffer,clean)
   except Exception:raise ExtraInputError("이 PDF의 원래 글꼴을 재사용할 수 없습니다.")
  self.cache[name]=entry;return entry
 def choose(self,name,text,mode="auto"):
  if mode not in {"auto","strict","noto"}:raise ExtraInputError("글꼴 모드를 확인하세요.")
  if mode!="noto":
   try:
    entry=self.original(name)
    if all(c.isspace() or entry[0].has_glyph(ord(c),fallback=False) for c in text):return entry
   except ExtraInputError:
    if mode=="strict":raise
   if mode=="strict":raise ExtraInputError("원래 글꼴에 새 글자가 없습니다. 대체 글꼴 허용을 선택하거나 문장을 바꾸세요.")
  if not all(c.isspace() or self.fallback.has_glyph(ord(c),fallback=False) for c in text):
   raise ExtraInputError("지원 글꼴에 없는 글자가 포함되어 있습니다. 이모지·특수 문자를 확인하세요.")
  self.fallback_names.add(name);self.fallback_count=len(self.fallback_names)
  return self.fallback_entry
 def install(self,entry):
  font,resource,buffer,_=entry
  self.page.insert_font(fontname=resource,fontbuffer=buffer)
  return resource

def paragraphs(page):
 result=[]
 for index,block in enumerate(page.get_text("dict")["blocks"]):
  if "lines" not in block:continue
  lines=block["lines"];text=" ".join("".join(s["text"] for s in line["spans"]) for line in lines)
  spans=[span for line in lines for span in line["spans"]]
  if not text.strip():continue
  result.append({"id":str(index),"text":text,"bbox":list(block["bbox"]),
   "fonts":sorted({span["font"] for span in spans}),"size":spans[0]["size"],
   "supported":not page.rotation and all(tuple(line.get("dir",(1,0)))==(1,0) for line in lines)})
 return result

def get_paragraphs(data,page_number):
 with open_pdf(data) as doc:
  number=int(page_number)
  if not 1<=number<=len(doc):raise ExtraInputError("페이지 번호를 확인하세요.")
  page=doc[number-1]
  return {"page":number,"pages":len(doc),"width":page.rect.width,"height":page.rect.height,"paragraphs":paragraphs(page)}

def original_characters(page,index):
 block=page.get_text("dict")["blocks"][index];chars=[]
 for line in block.get("lines",[]):
  if chars:chars.append((" ",chars[-1][1]))
  for span in line["spans"]:
   style=(span["font"],float(span["size"]),int(span["color"]))
   chars.extend((char,style) for char in span["text"])
 return chars

def styled_replacement(original,text):
 old="".join(c for c,_ in original);result=[]
 for op,i1,i2,j1,j2 in difflib.SequenceMatcher(a=old,b=text,autojunk=False).get_opcodes():
  if op=="equal":result.extend(original[i1:i2])
  elif op in {"insert","replace"}:
   style=original[min(i1,len(original)-1)][1]
   result.extend((char,style) for char in text[j1:j2])
 return result

def layout_paragraph(chars,manager,rect,mode,leading,alignment,unbounded=False):
 # Resolve per glyph so a new Korean character does not replace the original
 # Latin typeface elsewhere in the same paragraph.
 fonts={};resolved=[]
 for char,style in chars:
  entry=manager.choose(style[0],char,mode);key=(entry[1],style[1],style[2]);fonts[key]=entry;resolved.append((char,key))
 chars=resolved
 tokens=[];word=[]
 for item in chars:
  char=item[0]
  if char=="\n" or char.isspace() or ord(char)>0x2fff:
   if word:tokens.append(word);word=[]
   tokens.append([item])
  else:word.append(item)
 if word:tokens.append(word)
 lines=[];line=[];width=0
 def measure(item):return fonts[item[1]][0].text_length(item[0],fontsize=item[1][1])
 def finish():
  nonlocal line,width
  while line and line[-1][0].isspace():line.pop()
  lines.append(line);line=[];width=0
 for token in tokens:
  if token[0][0]=="\n":finish();continue
  tw=sum(measure(item) for item in token)
  if width+tw>rect.width and line:finish()
  if tw>rect.width:
   for item in token:
    cw=measure(item)
    if width+cw>rect.width and line:finish()
    if cw>rect.width:raise ExtraInputError("문단 폭이 한 글자보다 좁습니다.")
    line.append(item);width+=cw
  elif line or not all(item[0].isspace() for item in token):line.extend(token);width+=tw
 if line:finish()
 y=rect.y0;output=[]
 for line in lines:
  if not line:y+=12*leading;continue
  ascent=max(fonts[style][0].ascender*style[1] for _,style in line)
  descent=max(-fonts[style][0].descender*style[1] for _,style in line)
  height=max(style[1] for _,style in line)*leading
  if not unbounded and y+ascent+descent>rect.y1+.01:raise ExtraInputError("문단이 지정 영역에 들어가지 않습니다. 높이를 늘리거나 글자를 줄이세요. 잘라서 저장하지 않습니다.")
  baseline=y+ascent;line_width=sum(measure(item) for item in line)
  x=rect.x0+(rect.width-line_width)*({"left":0,"center":.5,"right":1}[alignment])
  runs=[]
  for char,style in line:
   if runs and runs[-1][1]==style:runs[-1]=(runs[-1][0]+char,style)
   else:runs.append((char,style))
  for text,style in runs:
   entry=fonts[style];output.append((x,baseline,text,style,entry));x+=entry[0].text_length(text,fontsize=style[1])
  y+=max(height,ascent+descent)
 return output,len(lines)

def reflow_paragraph(data,payload):
 if payload.get('flowMode')=='columns':
  from pdf_columns import column_flow
  return column_flow(data,payload)
 if payload.get('flow') is True:return flow_document(data,payload)
 with open_pdf(data) as doc:
  number=int(payload.get("page",1));index=int(payload.get("id",-1))
  if not 1<=number<=len(doc):raise ExtraInputError("페이지 번호를 확인하세요.")
  page=doc[number-1];selected=next((p for p in paragraphs(page) if p["id"]==str(index)),None)
  if not selected or not selected["supported"] or payload.get("original")!=selected["text"]:raise ExtraInputError("원문 문단을 다시 선택하세요.")
  text=payload.get("text","")
  if not isinstance(text,str) or not text.strip() or len(text)>10000 or any(ord(c)<32 and c not in '\n\t' for c in text):raise ExtraInputError("문단은 1~10,000자로 입력하세요.")
  text=text.replace('\t','    ')
  target=rect_for(page,payload);original_rect=pymupdf.Rect(selected["bbox"])
  # Do not paint over another paragraph/image, even when the user enlarges/moves a box.
  for bi,block in enumerate(page.get_text("dict")["blocks"]):
   if bi!=index and target.intersects(pymupdf.Rect(block["bbox"])):raise ExtraInputError("새 문단 영역이 다른 글자·이미지와 겹칩니다. 빈 공간으로 옮기거나 크기를 줄이세요.")
  if any((target.intersects(w.rect) or original_rect.intersects(w.rect)) for w in page.widgets() or []):raise ExtraInputError("양식 필드와 겹친 문단은 PDF 양식 도구를 사용하세요.")
  leading=float(payload.get("leading",1.4));alignment=payload.get("alignment","left")
  if not math.isfinite(leading) or not 1<=leading<=3 or alignment not in {"left","center","right"}:raise ExtraInputError("줄 간격·정렬을 확인하세요.")
  manager=FontManager(doc,page);original=original_characters(page,index)
  output,line_count=layout_paragraph(styled_replacement(original,text),manager,target,payload.get("fontMode","auto"),leading,alignment)
  # Check every deletion strip against all page glyphs before deleting anything.
  raw=page.get_text("rawdict")["blocks"];strips=[]
  for line in page.get_text("dict")["blocks"][index]["lines"]:
   r=pymupdf.Rect(line["bbox"]);mid=(r.y0+r.y1)/2;strips.append(pymupdf.Rect(r.x0,mid-r.height*.1,r.x1,mid+r.height*.1))
  for bi,block in enumerate(raw):
   for line in block.get("lines",[]):
    for span in line["spans"]:
     for char in span["chars"]:
      if char["c"].isspace():continue
      hit=any(strip.intersects(pymupdf.Rect(char["bbox"])) for strip in strips)
      if hit!=(bi==index):raise ExtraInputError("문단 글자가 다른 문단과 겹칩니다. 안전하게 삭제할 수 없어 작업을 중단했습니다.")
  for strip in strips:page.add_redact_annot(strip,fill=False,cross_out=False)
  page.apply_redactions(images=0,graphics=0,text=0)
  installed={}
  for x,y,text,style,entry in output:
   if entry[1] not in installed:installed[entry[1]]=manager.install(entry)
   color=tuple(((style[2]>>shift)&255)/255 for shift in (16,8,0))
   page.insert_text((x,y),text,fontsize=style[1],fontname=installed[entry[1]],color=color)
  return doc.tobytes(garbage=4,deflate=True),{"lines":line_count,"fallbackStyles":manager.fallback_count,"fonts":sorted({entry[3] for *_,entry in output})}

def flow_document(data,payload):
 """Reflow text-only single-column body from the selected paragraph onward."""
 import itertools
 with open_pdf(data) as doc:
  number=int(payload.get('page',1));index=str(payload.get('id',''));replacement=payload.get('text','')
  if not 1<=number<=len(doc):raise ExtraInputError("페이지 번호를 확인하세요.")
  if not isinstance(replacement,str) or not replacement.strip() or len(replacement)>10000 or any(ord(c)<32 and c not in '\n\t' for c in replacement):raise ExtraInputError("문단은 1~10,000자로 입력하세요.")
  replacement=replacement.replace('\t','    ')
  first=doc[number-1];target=rect_for(first,payload);selected=next((p for p in paragraphs(first) if p['id']==index),None)
  if not selected or payload.get('original')!=selected['text']:raise ExtraInputError("원문 문단을 다시 선택하세요.")
  if target.width<40 or target.height<30:raise ExtraInputError("자동 흐름을 위한 본문 영역을 넓혀 주세요.")
  leading=float(payload.get('leading',1.4));alignment=payload.get('alignment','left');mode=payload.get('fontMode','auto')
  if not math.isfinite(leading) or not 1<=leading<=3 or alignment not in {'left','center','right'}:raise ExtraInputError("줄 간격·정렬을 확인하세요.")
  page_width,page_height=first.rect.width,first.rect.height;plans=[];erasures={};font_names=set();fallback=0;line_total=0
  current_page=number-1;cursor=target.y0;bottom=target.y1;original_count=len(doc)
  for pi in range(number-1,original_count):
   page=doc[pi]
   if page.rotation or page.get_images() or page.get_drawings() or list(page.widgets() or []) or list(page.annots() or []) or page.get_links():raise ExtraInputError("자동 페이지 흐름은 이미지·도형·양식·주석·링크가 없는 가로 단일열 텍스트 문서에 사용하세요. 일반 문단 재배치는 그대로 사용할 수 있습니다.")
   if abs(page.rect.width-page_width)>1 or abs(page.rect.height-page_height)>1:raise ExtraInputError("자동 흐름에는 같은 크기의 페이지가 필요합니다.")
   blocks=sorted(paragraphs(page),key=lambda p:(p['bbox'][1],p['bbox'][0]))
   if any(not p['supported'] for p in blocks):raise ExtraInputError("회전·세로 글자가 있는 문서는 자동 흐름을 지원하지 않습니다.")
   if any(pymupdf.Rect(a['bbox']).y1>pymupdf.Rect(b['bbox']).y0+.5 for a,b in zip(blocks,blocks[1:])):raise ExtraInputError("겹친 문단·다단 문서의 자동 흐름은 지원하지 않습니다.")
   if pi==number-1:
    selected_position=next((i for i,p in enumerate(blocks) if p['id']==index),None)
    if selected_position is None:raise ExtraInputError("선택 문단을 찾을 수 없습니다.")
    before=blocks[:selected_position]
    if before and target.y0<max(p['bbox'][3] for p in before)+2:raise ExtraInputError("시작 영역이 앞 문단과 겹칩니다.")
    blocks=blocks[selected_position:]
   manager=FontManager(doc,page);strips=[];ids={p['id'] for p in blocks}
   for block in blocks:
    original=original_characters(page,int(block['id']));chars=styled_replacement(original,replacement) if pi==number-1 and block['id']==index else original
    output,count=layout_paragraph(chars,manager,pymupdf.Rect(target.x0,0,target.x1,1e9),mode,leading,alignment,unbounded=True)
    line_total+=count
    groups=[list(group) for _,group in itertools.groupby(output,key=lambda run:round(run[1],6))]
    previous_source_y=None;previous_height=0;previous_ascent=0
    for group in groups:
     ascent=max(run[4][0].ascender*run[3][1] for run in group);descent=max(-run[4][0].descender*run[3][1] for run in group)
     height=max(max(run[3][1] for run in group)*leading,ascent+descent)
     if previous_source_y is not None:
      extra=max(0,group[0][1]-previous_source_y-previous_height-(ascent-previous_ascent))
      cursor+=extra
     if cursor+ascent+descent>bottom+.01:
      current_page+=1;cursor=50;bottom=page_height-50
      if current_page>=200:raise ExtraInputError("자동 흐름 결과가 200쪽을 초과했습니다.")
     if cursor+ascent+descent>bottom:raise ExtraInputError("본문 영역에 한 줄이 들어가지 않습니다.")
     for x,source_y,text,style,entry in group:
      plans.append((current_page,x,cursor+ascent,text,style,entry));font_names.add(entry[3])
     cursor+=height;previous_source_y=group[0][1];previous_height=height;previous_ascent=ascent
    cursor+=max((style[1] for _,style in original),default=12)*.6
    for line in page.get_text('dict')['blocks'][int(block['id'])]['lines']:
     rect=pymupdf.Rect(line['bbox']);mid=(rect.y0+rect.y1)/2;strips.append(pymupdf.Rect(rect.x0,mid-rect.height*.1,rect.x1,mid+rect.height*.1))
   for bi,raw in enumerate(page.get_text('rawdict')['blocks']):
    for line in raw.get('lines',[]):
     for span in line['spans']:
      for char in span['chars']:
       if char['c'].isspace():continue
       hit=any(rect.intersects(pymupdf.Rect(char['bbox'])) for rect in strips)
       if hit!=(str(bi) in ids):raise ExtraInputError("주변 글자와 겹쳐 원문을 안전하게 제거할 수 없습니다.")
   erasures[pi]=strips;fallback+=manager.fallback_count
  if not plans:raise ExtraInputError("재배치할 본문이 없습니다.")
  for pi,strips in erasures.items():
   page=doc[pi]
   for rect in strips:page.add_redact_annot(rect,fill=False,cross_out=False)
   if strips:page.apply_redactions(images=0,graphics=0,text=0)
  last_page=max(plan[0] for plan in plans)
  while len(doc)<=last_page:doc.new_page(width=page_width,height=page_height)
  if len(doc)>last_page+1:doc.delete_pages(last_page+1,len(doc)-1)
  installed=set()
  for pi,x,y,text,style,entry in plans:
   page=doc[pi];key=(pi,entry[1])
   if key not in installed:page.insert_font(fontname=entry[1],fontbuffer=entry[2]);installed.add(key)
   color=tuple(((style[2]>>shift)&255)/255 for shift in (16,8,0))
   page.insert_text((x,y),text,fontsize=style[1],fontname=entry[1],color=color)
  return doc.tobytes(garbage=4,deflate=True),{'lines':line_total,'fallbackStyles':fallback,'fonts':sorted(font_names),'pages':len(doc),'flow':True}
