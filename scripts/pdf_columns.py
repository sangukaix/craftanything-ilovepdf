"""Conservative equal-width two/three-column text flow with fixed obstacles.

Layout is explicit, not inferred from arbitrary PDF reading order. Figures, tables,
wide headings and margin text remain fixed; ambiguous selected blocks are refused.
"""
import itertools
import math
import pymupdf
from pdf_extra import ExtraInputError,open_pdf
from pdf_layout import FontManager,paragraphs,original_characters,styled_replacement,layout_paragraph

def column_flow(data,payload):
 with open_pdf(data) as doc:
  try:
   number=int(payload.get('page',1));count=int(payload.get('columns',2));gutter=float(payload.get('gutter',24));margin=float(payload.get('margin',50));top=float(payload.get('bodyTop',80));bottom=float(payload.get('bodyBottom',doc[0].rect.height-60));leading=float(payload.get('leading',1.4))
  except (ValueError,TypeError):raise ExtraInputError('단·여백·줄 간격을 확인하세요.')
  if not 1<=number<=len(doc) or count not in {2,3} or not all(math.isfinite(v) for v in [gutter,margin,top,bottom,leading]) or not 8<=gutter<=100 or not 10<=margin<=150 or not 1<=leading<=3:raise ExtraInputError('2~3단, 단 간격 8~100pt, 좌우 여백 10~150pt를 사용하세요.')
  width,height=doc[number-1].rect.width,doc[number-1].rect.height
  col_width=(width-2*margin-(count-1)*gutter)/count
  if col_width<60 or top<10 or bottom>height-10 or bottom-top<60:raise ExtraInputError('본문 영역과 단 너비를 넓혀 주세요.')
  columns=[pymupdf.Rect(margin+c*(col_width+gutter),top,margin+c*(col_width+gutter)+col_width,bottom) for c in range(count)]
  text=payload.get('text','');selected_id=str(payload.get('id',''));mode=payload.get('fontMode','auto');alignment=payload.get('alignment','left')
  if alignment not in {'left','center','right'} or not isinstance(text,str) or not text.strip() or len(text)>10000 or any(ord(c)<32 and c not in '\n\t' for c in text):raise ExtraInputError('문단 내용·정렬을 확인하세요.')
  text=text.replace('\t','    ')
  sequence=[];obstacles={};erase={};selected_seen=False;start_col=None;start_y=None;fixed_total=0
  for pi in range(number-1,len(doc)):
   page=doc[pi]
   if page.rotation or abs(page.rect.width-width)>1 or abs(page.rect.height-height)>1:raise ExtraInputError('다단 흐름은 회전하지 않은 같은 크기의 페이지를 사용하세요.')
   blocks=page.get_text('dict')['blocks'];fixed=[]
   for block in blocks:
    if 'lines' not in block:fixed.append(pymupdf.Rect(block['bbox']))
   fixed.extend(pymupdf.Rect(d['rect']) for d in page.get_drawings())
   fixed.extend(pymupdf.Rect(w.rect) for w in page.widgets() or [])
   fixed.extend(pymupdf.Rect(a.rect) for a in page.annots() or [])
   fixed.extend(pymupdf.Rect(link['from']) for link in page.get_links())
   # Inflate also zero-width table borders, so their cell text is fixed.
   fixed=[r+(-3,-3,3,3) for r in fixed]
   # Connected vector edges form one fixed figure/table, including its interior.
   merged=[]
   for rect in fixed:
    changed=True
    while changed:
     changed=False;remaining=[]
     for prior in merged:
      if rect.intersects(prior):rect=rect|prior;changed=True
      else:remaining.append(prior)
     merged=remaining
    merged.append(rect)
   fixed=merged
   candidates=[];all_paragraphs=paragraphs(page)
   for block in all_paragraphs:
    rect=pymupdf.Rect(block['bbox']);col=next((c for c,r in enumerate(columns) if r.contains(rect)),None)
    if col is not None and block['supported'] and not any(rect.intersects(r) for r in fixed):candidates.append((col,rect.y0,block))
    else:fixed.append(rect+(-2,-2,2,2))
   candidates.sort(key=lambda item:(item[0],item[1],item[2]['bbox'][0]))
   # Overlapping source text is ambiguous, even if its bounding boxes fit a column.
   for a,b in zip(candidates,candidates[1:]):
    if a[0]==b[0] and pymupdf.Rect(a[2]['bbox']).intersects(pymupdf.Rect(b[2]['bbox'])):raise ExtraInputError('겹친 본문 블록은 다단 자동 흐름을 지원하지 않습니다.')
   erase_ids=set()
   for col,y,block in candidates:
    if not selected_seen:
     if pi==number-1 and block['id']==selected_id:
      if block['text']!=payload.get('original'):raise ExtraInputError('원문 문단을 다시 선택하세요.')
      selected_seen=True;start_col=col;start_y=max(top,y)
     else:fixed.append(pymupdf.Rect(block['bbox'])+(-2,-2,2,2));continue
    sequence.append((pi,block));erase_ids.add(block['id'])
   if pi==number-1 and not selected_seen:raise ExtraInputError('선택 문단이 지정한 단 안에 완전히 들어가지 않거나 표·그림·주석과 겹칩니다. 본문 영역·단 간격을 조정하거나 일반 문단 편집을 사용하세요.')
   obstacles[pi]=fixed;fixed_total+=len(fixed);strips=[]
   for index in erase_ids:
    for line in blocks[int(index)]['lines']:
     r=pymupdf.Rect(line['bbox']);mid=(r.y0+r.y1)/2;strips.append(pymupdf.Rect(r.x0,mid-r.height*.1,r.x1,mid+r.height*.1))
   for bi,block in enumerate(page.get_text('rawdict')['blocks']):
    for line in block.get('lines',[]):
     for span in line['spans']:
      for char in span['chars']:
       if char['c'].isspace():continue
       if any(r.intersects(pymupdf.Rect(char['bbox'])) for r in strips)!=(str(bi) in erase_ids):raise ExtraInputError('다른 글자와 겹쳐 원문을 안전하게 지울 수 없습니다.')
   erase[pi]=strips
  plans=[];pi=number-1;ci=start_col;cursor=start_y;line_total=0;names=set();managers={}
  for source_pi,block in sequence:
   if source_pi not in managers:managers[source_pi]=FontManager(doc,doc[source_pi])
   manager=managers[source_pi];original=original_characters(doc[source_pi],int(block['id']))
   chars=styled_replacement(original,text) if source_pi==number-1 and block['id']==selected_id else original
   runs,lines=layout_paragraph(chars,manager,pymupdf.Rect(0,0,col_width,1e9),mode,leading,alignment,unbounded=True);line_total+=lines
   previous_y=None;previous_height=0;previous_ascent=0
   for source_y,group_iter in itertools.groupby(runs,key=lambda run:round(run[1],6)):
    group=list(group_iter);ascent=max(r[4][0].ascender*r[3][1] for r in group);descent=max(-r[4][0].descender*r[3][1] for r in group)
    line_height=max(max(r[3][1] for r in group)*leading,ascent+descent)
    if previous_y is not None:cursor+=max(0,source_y-previous_y-previous_height-(ascent-previous_ascent))
    for attempt in range(20000):
     if pi>=200:raise ExtraInputError('다단 흐름 결과가 200쪽을 초과했습니다.')
     region=columns[ci]
     if cursor+line_height>bottom+.01:
      ci+=1;cursor=top
      if ci==count:pi+=1;ci=0
      continue
     line_rect=pymupdf.Rect(region.x0,cursor,region.x1,cursor+line_height)
     collisions=[r for r in obstacles.get(pi,[]) if line_rect.intersects(r)]
     if collisions:cursor=max(r.y1 for r in collisions)+3;continue
     break
    else:raise ExtraInputError('본문 배치 공간을 찾지 못했습니다.')
    for x,_,word,style,entry in group:plans.append((pi,region.x0+x,cursor+ascent,word,style,entry));names.add(entry[3])
    cursor+=line_height;previous_y=source_y;previous_height=line_height;previous_ascent=ascent
   cursor+=max((style[1] for _,style in original),default=12)*.6
  if not plans:raise ExtraInputError('재배치할 본문이 없습니다.')
  for page_no,strips in erase.items():
   page=doc[page_no]
   for r in strips:page.add_redact_annot(r,fill=False,cross_out=False)
   if strips:page.apply_redactions(images=0,graphics=0,text=0)
  while len(doc)<=max(plan[0] for plan in plans):doc.new_page(width=width,height=height)
  installed=set()
  for page_no,x,y,word,style,entry in plans:
   page=doc[page_no];key=(page_no,entry[1])
   if key not in installed:page.insert_font(fontname=entry[1],fontbuffer=entry[2]);installed.add(key)
   page.insert_text((x,y),word,fontsize=style[1],fontname=entry[1],color=tuple(((style[2]>>s)&255)/255 for s in (16,8,0)))
  return doc.tobytes(garbage=4,deflate=True),{'flow':True,'flowMode':'columns','columns':count,'pages':len(doc),'lines':line_total,'fonts':sorted(names),'fallbackStyles':sum(m.fallback_count for m in managers.values()),'fixedObjects':fixed_total,'paragraphs':len(sequence)}
