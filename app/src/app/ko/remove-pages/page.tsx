"use client";
import {useState,type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
import {downloadDocument} from "../local-api";
import {pagesToRemove} from "./remove";
import {useReady} from "../use-ready";
export default function Page(){
 const ready=useReady();
 const [file,setFile]=useState<File|null>(null),[range,setRange]=useState(""),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하 PDF를 사용하세요.");return;}setFile(files[0]);setStatus("");setRange("");}
 const dragging=useFileDrop(receive,busy);
 function choose(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function remove(){if(!file||busy)return;setBusy(true);try{const {PDFDocument}=await import("pdf-lib"),doc=await PDFDocument.load(await file.arrayBuffer());const indices=pagesToRemove(range,doc.getPageCount());const removed=new Set(indices),result=await PDFDocument.create(),kept=await result.copyPages(doc,doc.getPageIndices().filter(index=>!removed.has(index)));kept.forEach(page=>result.addPage(page));downloadDocument(new Blob([new Uint8Array(await result.save())],{type:"application/pdf"}),"pages-removed.pdf");setStatus(`완료: ${indices.length}쪽을 삭제한 새 PDF를 다운로드했습니다. 원본은 보존됩니다.`);}catch(e){setStatus(e instanceof Error?e.message:"페이지를 삭제하지 못했습니다.");}finally{setBusy(false);}}
 return <section className="tool-content">{dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아주세요</div>}<h1>PDF 페이지 삭제</h1><h2>원하지 않는 페이지를 제거한 새 PDF를 만듭니다.</h2><div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={!ready||busy} onChange={choose}/></label></div><div className="tool-work"><p>파일은 이 브라우저에서 처리됩니다. 원본 파일은 보존되며 결과의 기존 전자서명은 유효하지 않을 수 있습니다.</p>{file&&<><p>{file.name}</p><label>삭제할 페이지<input value={range} disabled={!ready||busy} onChange={e=>setRange(e.target.value)} placeholder="예: 2,4-6"/></label><button className="tool-run" disabled={!ready||busy||!range.trim()} onClick={remove}>페이지 삭제 PDF 다운로드</button></>}<p role="status">{status}</p></div></section>;
}
