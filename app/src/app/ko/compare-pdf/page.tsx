"use client";
import {useState, type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
type Preview={image:string;text:string;pages:number};
export default function Page(){
 const [files,setFiles]=useState<File[]>([]),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 const [views,setViews]=useState<Preview[]>([]),[page,setPage]=useState(1);
 function receive(incoming:File[]){
  if(busy)return;const error=validateFiles(incoming,".pdf,application/pdf",true);if(error){setStatus(error);return;}
  const next=incoming.length===2?incoming:[...files,...incoming];
  if(next.length>2){setStatus("비교할 PDF를 두 개만 선택하세요.");return;}
  setFiles(next);setViews([]);setPage(1);setStatus("");
 }
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function compare(target:number){
  if(files.length!==2||busy)return;setBusy(true);setStatus("두 PDF를 읽고 있습니다…");
  try{
   const pdfjs=await import("pdfjs-dist");pdfjs.GlobalWorkerOptions.workerSrc="/pdfjs/pdf.worker.min.mjs";
   const next:Preview[]=[];
   for(const file of files){
    const task=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),cMapUrl:"/pdfjs/cmaps/",cMapPacked:true,standardFontDataUrl:"/pdfjs/standard_fonts/",wasmUrl:"/pdfjs/wasm/"});
    try{
     const doc=await task.promise;
     if(target>doc.numPages){next.push({image:"",text:"",pages:doc.numPages});continue;}
     const p=await doc.getPage(target),base=p.getViewport({scale:1});const viewport=p.getViewport({scale:Math.min(1.25,1600/Math.max(base.width,base.height))});
     const canvas=document.createElement("canvas");canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
     const ctx=canvas.getContext("2d");if(!ctx)throw new Error("페이지 미리보기를 만들 수 없습니다.");
     await p.render({canvas,canvasContext:ctx,viewport}).promise;
     const content=await p.getTextContent();const text=content.items.map(item=>"str" in item?item.str:"").join(" ").replace(/\s+/g," ").trim();
     next.push({image:canvas.toDataURL("image/png"),text,pages:doc.numPages});canvas.width=1;canvas.height=1;
    }finally{await task.destroy();}
   }
   setViews(next);setPage(target);setStatus(next.some(v=>!v.image)?"한 문서에 해당 페이지가 없습니다.":!next[0].text&&!next[1].text?"추출 가능한 텍스트가 없어 화면을 직접 비교하세요.":next[0].text===next[1].text?"이 페이지의 추출 텍스트가 같습니다. 화면 배치는 직접 확인하세요.":"이 페이지의 추출 텍스트가 다릅니다.");
  }catch(e){setViews([]);setStatus("비교하지 못했습니다. "+(e instanceof Error?e.message:"파일을 확인하세요."));}finally{setBusy(false);}
 }
 const maxPage=views.length?Math.max(...views.map(v=>v.pages)):1;
 return <section className="tool-content">
  {dragging&&<div className="file-drop-overlay" role="status">비교할 PDF 두 개를 놓아주세요</div>}
  <h1>PDF 비교</h1><h2>두 PDF의 페이지를 나란히 보고 추출 텍스트를 비교합니다.</h2>
  <div className="tool-picker"><label className="tool-file-button">PDF 두 개 선택<input type="file" multiple accept=".pdf,application/pdf" onChange={select} disabled={busy}/></label></div>
  <p className="tool-drop">PDF를 하나씩 또는 두 개 함께 화면에 놓으세요.</p>
  <div className="tool-work"><ol>{files.map((file,i)=><li key={i}>{file.name} <button disabled={busy} onClick={()=>{setFiles(old=>old.filter((_,n)=>n!==i));setViews([]);setStatus("");}} aria-label={`${file.name} 제거`}>×</button></li>)}</ol>
   <p>파일은 브라우저에서 처리됩니다. 자동 비교는 텍스트 기준이며 이미지·서식 변경을 자동 강조하지 않습니다.</p>
   <button className="tool-run" disabled={busy||files.length!==2} onClick={()=>compare(1)}>{busy?"처리 중…":"PDF 비교하기"}</button><p role="status">{status}</p>
  </div>
  {views.length===2&&<><div style={{display:"flex",justifyContent:"center",gap:16,alignItems:"center",margin:16}}><button disabled={busy||page<=1} onClick={()=>compare(page-1)}>이전 페이지</button><span>{page} / {maxPage}</span><button disabled={busy||page>=maxPage} onClick={()=>compare(page+1)}>다음 페이지</button></div>
   <div style={{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:16,alignItems:"start",maxWidth:1400,margin:"0 auto 32px"}}>{views.map((v,i)=><article key={i} style={{minWidth:0}}><h3 style={{overflowWrap:"anywhere"}}>{files[i].name} · {v.pages}쪽</h3>{v.image?<img src={v.image} alt={`${files[i].name} ${page}쪽`} style={{width:"100%",border:"1px solid #ccc",background:"white"}}/>:<p>해당 페이지 없음</p>}<details><summary>추출 텍스트 보기</summary><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere",textAlign:"left"}}>{v.text||"텍스트 없음"}</p></details></article>)}</div></>}
 </section>;
}
