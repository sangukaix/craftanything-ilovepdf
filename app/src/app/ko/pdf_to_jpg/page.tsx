"use client";
import {useState, type ChangeEvent} from "react";
import {validateFiles} from "../file-drop";
import {useFileDrop} from "../use-file-drop";
export default function Page(){
 const [file,setFile]=useState<File|null>(null),[status,setStatus]=useState(""),[busy,setBusy]=useState(false);
 const dragging=useFileDrop(receive,busy);
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}setFile(files[0]);setStatus("");}
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function convert(){
  if(!file||busy)return;setBusy(true);setStatus("PDF를 읽고 있습니다…");
  let loading:Awaited<ReturnType<typeof import("pdfjs-dist")["getDocument"]>>|null=null;
  try{
   const pdfjs=await import("pdfjs-dist");const {default:JSZip}=await import("jszip");
   pdfjs.GlobalWorkerOptions.workerSrc="/pdfjs/pdf.worker.min.mjs";
   loading=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),cMapUrl:"/pdfjs/cmaps/",cMapPacked:true,standardFontDataUrl:"/pdfjs/standard_fonts/",wasmUrl:"/pdfjs/wasm/"});
   const doc=await loading.promise;if(doc.numPages>100)throw new Error("한 번에 100쪽까지 변환할 수 있습니다.");
   const zip=new JSZip();
   for(let i=1;i<=doc.numPages;i++){
    setStatus(`${i} / ${doc.numPages}쪽을 이미지로 만드는 중…`);
    const page=await doc.getPage(i),base=page.getViewport({scale:1});const scale=Math.min(1.5,4096/Math.max(base.width,base.height));const viewport=page.getViewport({scale});
    const canvas=document.createElement("canvas");canvas.width=Math.max(1,Math.ceil(viewport.width));canvas.height=Math.max(1,Math.ceil(viewport.height));
    const ctx=canvas.getContext("2d");if(!ctx)throw new Error("이미지 생성 기능을 사용할 수 없습니다.");ctx.fillStyle="white";ctx.fillRect(0,0,canvas.width,canvas.height);
    await page.render({canvas,canvasContext:ctx,viewport}).promise;
    const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error("JPG 생성 실패")),"image/jpeg",.9));
    zip.file(`page-${String(i).padStart(3,"0")}.jpg`,blob);page.cleanup();canvas.width=1;canvas.height=1;
   }
   const zipBlob=await zip.generateAsync({type:"blob"});const url=URL.createObjectURL(zipBlob);const a=document.createElement("a");a.href=url;a.download="pdf-pages-jpg.zip";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);setStatus(`완료했습니다. ${doc.numPages}쪽의 JPG가 담긴 ZIP을 다운로드했습니다.`);
  }catch(e){setStatus("변환하지 못했습니다. 파일 형식과 암호 보호 여부를 확인하세요. "+(e instanceof Error?e.message:""));}finally{if(loading)await loading.destroy();setBusy(false);}
 }
 return <section className={`tool-content${dragging?" is-dragging":""}`}>{dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아 추가하세요</div>}<h1>PDF JPG 변환</h1><h2>PDF 페이지를 JPG 이미지로 변환합니다.</h2><div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" onChange={select} disabled={busy}/></label></div><p className="tool-drop">또는 PDF를 여기에 두기</p>{!file&&status&&<p role="status">{status}</p>}{file&&<div className="tool-work"><p>{file.name} · 파일은 브라우저에서 처리됩니다.</p><button type="button" className="tool-run" onClick={convert} disabled={busy}>{busy?"변환 중…":"JPG로 변환"}</button><p role="status">{status}</p></div>}</section>
}
