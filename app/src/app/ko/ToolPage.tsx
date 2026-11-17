"use client";
import CloudButtons from "./CloudButtons";
import { useState, type ChangeEvent } from "react";
import { validateFiles } from "./file-drop";
import {useFileDrop} from "./use-file-drop";
type Props={title:string; description:string; button:string; accept:string; multiple:boolean; drop:string};
type Mode="merge"|"split"|"jpg"|"rotate"|"organize"|"number"|"watermark"|"crop"|"unavailable";
function selectedPages(value:string,count:number):number[] {
  if (!value.trim()) return Array.from({length:count},(_,i)=>i);
  const found:number[]=[];
  for (const part of value.split(",")) {
    const match=part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) throw new Error("페이지 범위를 1-3,5처럼 입력하세요.");
    const start=Number(match[1]),end=Number(match[2] || match[1]);
    if (start<1 || end<start || end>count) throw new Error(`페이지 범위는 1부터 ${count}까지입니다.`);
    for(let n=start;n<=end;n++) if(!found.includes(n-1)) found.push(n-1);
  }
  return found;
}
export default function ToolPage({title,description,button,accept,multiple,drop}:Props) {
 const [files,setFiles]=useState<File[]>([]), [range,setRange]=useState(""), [angle,setAngle]=useState("90"), [watermark,setWatermark]=useState(""), [margin,setMargin]=useState("36"), [message,setMessage]=useState(""), [busy,setBusy]=useState(false);
 const mode:Mode=title==="PDF 합치기"?"merge":title==="PDF 분할"?"split":title==="JPG PDF 변환"?"jpg":title==="PDF 회전"?"rotate":title==="PDF 구성"?"organize":title==="페이지 번호"?"number":title==="워터마크"?"watermark":title==="PDF 자르기"?"crop":"unavailable";
 const dragging=useFileDrop(receive,busy);
 function receive(incoming:File[]){if(busy)return;const error=validateFiles(incoming,accept,multiple);if(error){setMessage(error);return;}setFiles(old=>multiple?[...old,...incoming.filter(f=>!old.some(x=>x.name===f.name&&x.size===f.size&&x.lastModified===f.lastModified))]:incoming);setMessage("");}
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 function move(index:number,delta:number){setFiles(old=>{const next=[...old],other=index+delta;if(other<0||other>=next.length)return old;[next[index],next[other]]=[next[other],next[index]];return next;});}
 async function run(){
  if(busy||!files.length)return;
  if(mode==="unavailable"){setMessage("이 기능은 아직 지원하지 않습니다.");return;}
  if(mode==="merge"&&files.length<2){setMessage("PDF 파일을 2개 이상 선택하세요.");return;}
  if(mode==="watermark"&&!watermark.trim()){setMessage("워터마크 문구를 입력하세요.");return;}
  if(mode==="crop"&&(!/^\d+(?:\.\d+)?$/.test(margin)||Number(margin)<0)){setMessage("여백을 0 이상의 숫자로 입력하세요.");return;}
  setBusy(true);setMessage("파일을 이 기기에서 처리하고 있습니다…");
  try {
   const {PDFDocument,degrees,StandardFonts,rgb}=await import("pdf-lib"); const result=await PDFDocument.create();
   if(mode==="jpg") {
    for(const file of files){const bytes=await file.arrayBuffer();const image=await result.embedJpg(bytes);const page=result.addPage([image.width,image.height]);page.drawImage(image,{x:0,y:0,width:image.width,height:image.height});}
   } else if(mode==="merge") {
    for(const file of files){const source=await PDFDocument.load(await file.arrayBuffer());const pages=await result.copyPages(source,source.getPageIndices());pages.forEach(page=>result.addPage(page));}
   } else {
    const source=await PDFDocument.load(await files[0].arrayBuffer());
    const indices=(mode==="split"||mode==="organize")?selectedPages(range,source.getPageCount()):source.getPageIndices();
    const pages=await result.copyPages(source,indices);
    const numberFont=mode==="number"?await result.embedFont(StandardFonts.Helvetica):null;
    let stamp:Awaited<ReturnType<typeof result.embedPng>>|null=null;
    if(mode==="watermark") {
      await document.fonts.load('700 52px "Noto Sans KR"');
      const canvas=document.createElement("canvas");
      const ctx=canvas.getContext("2d");if(!ctx)throw new Error("워터마크 캔버스를 만들 수 없습니다.");
      ctx.font='700 52px "Noto Sans KR", sans-serif';canvas.width=Math.min(1600,Math.ceil(ctx.measureText(watermark.trim()).width)+80);canvas.height=110;
      ctx.font='700 52px "Noto Sans KR", sans-serif';ctx.fillStyle="#666666";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(watermark.trim(),canvas.width/2,55,canvas.width-40);
      const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(v=>v?resolve(v):reject(new Error("이미지 생성 실패")),"image/png"));stamp=await result.embedPng(await blob.arrayBuffer());
    }
    pages.forEach((page,index)=>{
      if(mode==="rotate")page.setRotation(degrees((page.getRotation().angle+Number(angle))%360));
      if(mode==="crop"){const box=page.getCropBox(),m=Number(margin);if(box.width<=2*m||box.height<=2*m)throw new Error("여백이 페이지보다 큽니다.");page.setCropBox(box.x+m,box.y+m,box.width-2*m,box.height-2*m);}
      if(numberFont){const label=String(index+1),size=12;page.drawText(label,{x:(page.getWidth()-numberFont.widthOfTextAtSize(label,size))/2,y:18,size,font:numberFont,color:rgb(.2,.2,.2)});}
      if(stamp){const width=Math.min(page.getWidth()*.8,480),height=width*stamp.height/stamp.width;page.drawImage(stamp,{x:(page.getWidth()-width)/2,y:(page.getHeight()-height)/2,width,height,opacity:.35});}
      result.addPage(page);
    });
   }
   const bytes=await result.save();const blob=new Blob([new Uint8Array(bytes)],{type:"application/pdf"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=mode==="merge"?"merged.pdf":mode==="split"?"selected-pages.pdf":mode==="rotate"?"rotated.pdf":mode==="organize"?"organized.pdf":mode==="number"?"numbered.pdf":mode==="watermark"?"watermarked.pdf":mode==="crop"?"cropped.pdf":"images.pdf";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);setMessage("완료했습니다. 다운로드한 PDF를 확인하세요.");
  } catch(error){setMessage("파일을 처리하지 못했습니다. 파일 형식과 암호 보호 여부를 확인하세요. " + (error instanceof Error ? error.message : ""));} finally{setBusy(false);}
 }
 return <section className={`tool-content${dragging?" is-dragging":""}`}>{dragging&&<div className="file-drop-overlay" role="status">파일을 놓아 추가하세요</div>}<h1>{title}</h1><h2>{description}</h2><div className="tool-picker"><label className="tool-file-button">{button}<input type="file" accept={accept} multiple={multiple} onChange={select} disabled={busy}/></label><CloudButtons/></div><p className="tool-drop">{drop}</p>{!files.length&&message&&<p role="status">{message}</p>}{files.length>0 && <div className="tool-work"><p>선택한 파일 {files.length}개 · 파일은 브라우저에서 처리됩니다.</p>{mode==="unavailable"&&<p role="note">파일은 인식했습니다. 이 도구의 처리 기능은 아직 구현되지 않았습니다.</p>}<ol>{files.map((file,i)=><li key={`${file.name}-${i}`}><span>{file.name}</span><button type="button" disabled={busy} onClick={()=>setFiles(old=>old.filter((_,n)=>n!==i))} aria-label={`${file.name} 제거`}>×</button>{multiple&&<><button type="button" onClick={()=>move(i,-1)} disabled={i===0} aria-label={`${file.name} 위로`}>↑</button><button type="button" onClick={()=>move(i,1)} disabled={i===files.length-1} aria-label={`${file.name} 아래로`}>↓</button></>}</li>)}</ol>{(mode==="split"||mode==="organize")&&<label>{mode==="organize"?"원하는 페이지 순서 (예: 3,1-2; 비우면 전체)":"추출할 페이지 (예: 1-3,5, 비우면 전체)"}<input value={range} onChange={e=>setRange(e.target.value)} placeholder="1-3,5" /></label>}{mode==="crop"&&<><label>각 가장자리에서 자를 여백 (포인트, 72pt = 1인치)<input type="number" min="0" step="1" value={margin} onChange={e=>setMargin(e.target.value)} /></label><p>자르기는 보이는 영역만 변경하며 원본 내용은 파일에 남습니다.</p></>}{mode==="watermark"&&<label>워터마크 문구<input value={watermark} onChange={e=>setWatermark(e.target.value)} maxLength={80} placeholder="문구 입력" /></label>}{mode==="rotate"&&<label>회전 각도<select value={angle} onChange={e=>setAngle(e.target.value)}><option value="90">시계 방향 90도</option><option value="180">180도</option><option value="270">반시계 방향 90도</option></select></label>}<button className="tool-run" type="button" disabled={busy || mode==="unavailable"} onClick={run}>{busy?"처리 중…":mode==="unavailable"?"아직 지원하지 않습니다":"PDF 만들기"}</button><p role="status">{message}</p></div>}</section>
}

