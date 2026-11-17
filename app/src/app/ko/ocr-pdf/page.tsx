"use client";
import {useRef,useState,type ChangeEvent} from "react";
import {validateFiles} from "../file-drop";
import {useFileDrop} from "../use-file-drop";
export default function Page(){
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState(""),[language,setLanguage]=useState("kor+eng");
 const cancelled=useRef(false);
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하의 PDF를 선택하세요.");return;}setFile(files[0]);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function run(){
  if(!file||busy)return;setBusy(true);cancelled.current=false;setStatus("OCR 인식기를 준비하고 있습니다…");
  let worker:Awaited<ReturnType<typeof import("tesseract.js")["createWorker"]>>|null=null;
  let task:Awaited<ReturnType<typeof import("pdfjs-dist")["getDocument"]>>|null=null;
  try{
   const pdfjs=await import("pdfjs-dist"),{PDFDocument}=await import("pdf-lib"),{createWorker}=await import("tesseract.js");
   pdfjs.GlobalWorkerOptions.workerSrc="/pdfjs/pdf.worker.min.mjs";
   const bytes=await file.arrayBuffer();task=pdfjs.getDocument({data:new Uint8Array(bytes.slice(0)),cMapUrl:"/pdfjs/cmaps/",cMapPacked:true,standardFontDataUrl:"/pdfjs/standard_fonts/",wasmUrl:"/pdfjs/wasm/"});
   const doc=await task.promise;if(doc.numPages>20)throw new Error("OCR은 한 번에 20쪽까지 지원합니다. 문서를 분할한 뒤 다시 시도하세요.");
   const source=await PDFDocument.load(bytes),result=await PDFDocument.create();let recognized=0,kept=0,currentPage=0;
   for(let i=1;i<=doc.numPages;i++){
    if(cancelled.current)throw new Error("OCR을 취소했습니다.");currentPage=i;setStatus(`${i}/${doc.numPages}쪽을 읽고 있습니다…`);
    const page=await doc.getPage(i),content=await page.getTextContent();
    if(content.items.some(item=>"str" in item&&item.str.trim())){
     const copied=await result.copyPages(source,[i-1]);result.addPage(copied[0]);kept++;page.cleanup();continue;
    }
    if(!worker){const root=location.origin;worker=await createWorker(language,1,{workerPath:root+"/ocr/worker.min.js",corePath:root+"/ocr/core",langPath:root+"/ocr/lang",gzip:false,workerBlobURL:false,logger:m=>{if(m.status==="recognizing text")setStatus(`${currentPage}/${doc.numPages}쪽 글자 인식 중… ${Math.round(m.progress*100)}%`);}});await worker.setParameters({user_defined_dpi:"144",preserve_interword_spaces:"1"});}
    const original=page.getViewport({scale:1}),viewport=page.getViewport({scale:Math.min(2,2600/Math.max(original.width,original.height))});
    const canvas=document.createElement("canvas");canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);const ctx=canvas.getContext("2d");if(!ctx)throw new Error("PDF 이미지를 만들 수 없습니다.");
    await page.render({canvas,canvasContext:ctx,viewport}).promise;
    const {data}=await worker.recognize(canvas,{pdfTitle:file.name,pdfTextOnly:false},{text:true,pdf:true});
    if(cancelled.current)throw new Error("OCR을 취소했습니다.");
    if(!data.pdf)throw new Error("검색 가능한 PDF를 생성하지 못했습니다.");
    const scanned=await PDFDocument.load(new Uint8Array(data.pdf));const [copied]=await result.copyPages(scanned,[0]);copied.scale(original.width/copied.getWidth(),original.height/copied.getHeight());result.addPage(copied);
    if(data.text.trim())recognized++;canvas.width=1;canvas.height=1;page.cleanup();
   }
   if(!recognized&&!kept)throw new Error("글자를 인식하지 못했습니다. 언어와 원본 이미지 해상도를 확인하세요.");
   const output=await result.save();const blob=new Blob([new Uint8Array(output)],{type:"application/pdf"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=file.name.replace(/\.pdf$/i,"")+"-ocr.pdf";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
   setStatus(`완료: OCR 인식 ${recognized}쪽, 기존 텍스트 보존 ${kept}쪽. 결과 PDF에서 검색·복사를 시험하세요. 인식하지 못한 페이지가 있을 수 있습니다.`);
  }catch(e){setStatus(e instanceof Error?e.message:"OCR 처리에 실패했습니다.");}
  finally{try{if(worker)await worker.terminate();}finally{try{if(task)await task.destroy();}finally{setBusy(false);}}}
 }
 return <section className="tool-content">
  {dragging&&<div className="file-drop-overlay" role="status">OCR할 PDF를 놓아주세요</div>}
  <h1>OCR PDF</h1><h2>스캔 문서의 한국어·영어를 인식해 검색 가능한 PDF로 만듭니다.</h2>
  <div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={select}/></label></div><p className="tool-drop">또는 PDF를 화면에 놓아 가져오기</p>
  <div className="tool-work"><p>최대 25MB·20쪽. 파일과 OCR 처리는 이 브라우저 안에서 이루어집니다. 이미 텍스트가 있는 페이지는 유지합니다. 스캔 페이지는 이미지와 인식한 텍스트로 재구성하며 양식·링크·전자서명을 보존하지 않습니다. 필기·흐린 글자·복잡한 배치는 오인식될 수 있습니다.</p>
   <label>인식 언어<select value={language} disabled={busy} onChange={e=>setLanguage(e.target.value)}><option value="kor+eng">한국어 + 영어</option><option value="eng">영어</option><option value="kor">한국어</option></select></label>
   {file&&<><p>{file.name}</p><button className="tool-run" disabled={busy} onClick={run}>{busy?"OCR 처리 중…":"검색 가능한 PDF 만들기"}</button></>}
   {busy&&<button className="tool-run" onClick={()=>{cancelled.current=true;setStatus("현재 페이지 처리가 끝나면 취소합니다…");}}>취소</button>}<p role="status">{status}</p>
  </div>
 </section>;
}
