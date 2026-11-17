"use client";
import {useState, type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
export default function Page(){
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}setFile(files[0]);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function convert(){
  if(!file||busy)return;setBusy(true);setStatus("PDF 텍스트를 읽고 있습니다…");
  let loading:Awaited<ReturnType<typeof import("pdfjs-dist")["getDocument"]>>|null=null;
  try{
   const pdfjs=await import("pdfjs-dist");pdfjs.GlobalWorkerOptions.workerSrc="/pdfjs/pdf.worker.min.mjs";
   loading=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),cMapUrl:"/pdfjs/cmaps/",cMapPacked:true,standardFontDataUrl:"/pdfjs/standard_fonts/",wasmUrl:"/pdfjs/wasm/"});
   const doc=await loading.promise;if(doc.numPages>200)throw new Error("한 번에 200쪽까지 처리할 수 있습니다.");
   const pages:string[]=[];let textLength=0;
   for(let i=1;i<=doc.numPages;i++){
    setStatus(`${i}/${doc.numPages}쪽 텍스트 추출 중…`);
    const page=await doc.getPage(i);const content=await page.getTextContent();let text="";
    for(const item of content.items){if("str" in item){text+=item.str+(item.hasEOL?"\n":" ");}}
    text=text.trim();textLength+=text.length;pages.push(`## ${i}쪽\n\n${text||"(추출 가능한 텍스트 없음)"}`);page.cleanup();
   }
   if(!textLength)throw new Error("추출 가능한 텍스트가 없습니다. 스캔한 PDF에는 별도의 OCR 기능이 필요합니다.");
   const blob=new Blob([pages.join("\n\n---\n\n")+"\n"],{type:"text/markdown;charset=utf-8"});const url=URL.createObjectURL(blob);
   const link=document.createElement("a");link.href=url;link.download=file.name.replace(/\.pdf$/i,"")+".md";document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
   setStatus(`완료했습니다. ${doc.numPages}쪽의 텍스트를 Markdown 파일로 저장했습니다.`);
  }catch(e){setStatus("변환하지 못했습니다. "+(e instanceof Error?e.message:"PDF 파일을 확인하세요."));}
  finally{try{if(loading)await loading.destroy();}finally{setBusy(false);}}
 }
 return <section className={`tool-content${dragging?" is-dragging":""}`}>
  {dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아 추가하세요</div>}
  <h1>PDF를 마크다운으로 변환</h1><h2>PDF의 텍스트를 추출해 Markdown 파일로 저장합니다.</h2>
  <div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" onChange={select} disabled={busy}/></label></div>
  <p className="tool-drop">또는 PDF를 화면에 놓아 가져오기</p>
  <div className="tool-work"><p>텍스트가 포함된 PDF를 지원합니다. 표·제목·여러 단의 배치는 자동 복원하지 않으며 스캔 문서의 OCR은 지원하지 않습니다. 파일은 이 브라우저에서 처리됩니다.</p>
   {file&&<><p>{file.name}</p><button type="button" className="tool-run" onClick={convert} disabled={busy}>{busy?"처리 중…":"Markdown 다운로드"}</button></>}
   <p role="status">{status}</p>
  </div>
 </section>;
}
