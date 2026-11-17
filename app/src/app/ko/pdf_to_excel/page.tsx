"use client";
import {useState,type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
import {textToRows,createWorkbook} from "./workbook";
export default function Page(){
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하의 PDF를 선택하세요.");return;}setFile(files[0]);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function convert(){
  if(!file||busy)return;setBusy(true);setStatus("PDF 텍스트를 읽고 있습니다…");
  let task:Awaited<ReturnType<typeof import("pdfjs-dist")["getDocument"]>>|null=null;
  try{
   const pdfjs=await import("pdfjs-dist");pdfjs.GlobalWorkerOptions.workerSrc="/pdfjs/pdf.worker.min.mjs";
   task=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),cMapUrl:"/pdfjs/cmaps/",cMapPacked:true,standardFontDataUrl:"/pdfjs/standard_fonts/",wasmUrl:"/pdfjs/wasm/"});
   const doc=await task.promise;if(doc.numPages>200)throw new Error("200쪽 이하의 PDF를 사용하세요.");
   const sheets:string[][][]=[];let textCount=0,emptyPages=0;
   for(let i=1;i<=doc.numPages;i++){
    setStatus(`${i}/${doc.numPages}쪽을 Excel 행과 열로 변환 중…`);
    const page=await doc.getPage(i),content=await page.getTextContent();
    const items=content.items.flatMap(item=>"str" in item?[{text:item.str,x:item.transform[4],y:item.transform[5],width:item.width,height:Math.max(1,item.height)}]:[]);
    const rows=textToRows(items);textCount+=items.reduce((sum,item)=>sum+item.text.trim().length,0);if(!rows.length)emptyPages++;
    sheets.push(rows.length?rows:[["추출 가능한 텍스트 없음 (OCR 필요)"]]);page.cleanup();
   }
   if(!textCount)throw new Error("추출 가능한 텍스트가 없습니다. 이미지로 스캔한 PDF에는 OCR이 필요합니다.");
   const bytes=await createWorkbook(sheets),blob=new Blob([new Uint8Array(bytes)],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
   const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=file.name.replace(/\.pdf$/i,"")+".xlsx";document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
   setStatus(`${doc.numPages}개 시트를 담은 Excel 파일을 다운로드했습니다.${emptyPages?` 텍스트 없는 ${emptyPages}쪽은 OCR이 필요합니다.`:""} 셀 배치는 원문과 대조해 확인하세요.`);
  }catch(e){setStatus("변환하지 못했습니다. "+(e instanceof Error?e.message:"PDF 파일을 확인하세요."));}
  finally{try{if(task)await task.destroy();}finally{setBusy(false);}}
 }
 return <section className={`tool-content${dragging?" is-dragging":""}`}>
  {dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아 추가하세요</div>}
  <h1>PDF 엑셀 변환</h1><h2>PDF의 텍스트를 행과 열로 추출해 Excel 파일로 저장합니다.</h2>
  <div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={select}/></label></div><p className="tool-drop">또는 PDF를 화면에 놓아 가져오기</p>
  <div className="tool-work"><p>텍스트 PDF를 지원하며 각 페이지를 별도 시트에 저장합니다. 표의 행·열은 글자 위치로 추정합니다. 스캔 OCR·이미지·수식·원본 서식 복원은 지원하지 않습니다. 숫자도 원문 보존을 위해 텍스트로 저장합니다. 파일은 브라우저에서만 처리됩니다.</p>
   {file&&<><p>{file.name}</p><button type="button" className="tool-run" disabled={busy} onClick={convert}>{busy?"변환 중…":"Excel로 변환"}</button></>}<p role="status">{status}</p>
  </div>
 </section>;
}
