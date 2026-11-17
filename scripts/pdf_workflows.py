"""Bounded, in-memory local PDF pipelines; passwords are never persisted."""
import math
import pymupdf
from pdf_extra import FONT,ExtraInputError,open_pdf

def run_workflow(data,steps,process_pdf,pdfa_convert):
 if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ExtraInputError("1~8단계 워크플로를 지정하세요.")
 result=data
 for index,step in enumerate(steps):
  operation=step.get('operation')
  if operation=='protect':
   if index!=len(steps)-1:raise ExtraInputError("암호 보호는 마지막 단계에만 사용할 수 있습니다.")
   result=process_pdf('protect',result,step.get('password',''))
  elif operation=='compress':result=process_pdf('compress',result)
  elif operation=='pdfa':
   if index!=len(steps)-1:raise ExtraInputError("PDF/A 변환·검사는 마지막 단계에 배치하세요. 이후 수정·암호 추가는 PDF/A 적합성을 보존하지 않습니다.")
   result=pdfa_convert(result)[0]
  elif operation in {'rotate','number','watermark'}:
   with open_pdf(result) as doc:
    for number,page in enumerate(doc):
     if operation=='rotate':
      angle=int(step.get('angle',90))
      if angle not in {90,180,270}:raise ExtraInputError("회전 각도를 확인하세요.")
      page.set_rotation((page.rotation+angle)%360)
     elif operation=='number':
      point=pymupdf.Point(max(10,page.rect.width/2-5),page.rect.height-18)*page.derotation_matrix
      page.insert_text(point,str(number+1),fontsize=11,rotate=page.rotation)
     else:
      text=step.get('text','')
      if not isinstance(text,str) or not text.strip() or len(text)>80:raise ExtraInputError("워터마크는 1~80자로 입력하세요.")
      font=pymupdf.Font(fontfile=str(FONT));size=min(32,(page.rect.width-50)/max(.1,font.text_length(text,fontsize=1)))
      if not math.isfinite(size) or size<6:raise ExtraInputError("워터마크 글자가 너무 깁니다.")
      x=(page.rect.width-font.text_length(text,fontsize=size))/2
      point=pymupdf.Point(x,page.rect.height/2)*page.derotation_matrix
      page.insert_text(point,text,fontsize=size,fontname='workflowNoto',fontfile=str(FONT),color=(.5,.5,.5),fill_opacity=.35,rotate=page.rotation)
    result=doc.tobytes(garbage=4,deflate=True)
  else:raise ExtraInputError("지원하지 않는 워크플로 단계입니다.")
 return result
