"use client";
import {useState,type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
import {postDocument,downloadDocument} from "../local-api";
export default function Page(){
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하 PDF를 사용하세요.");return;}setFile(files[0]);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(event:ChangeEvent<HTMLInputElement>){receive(Array.from(event.target.files||[]));event.target.value="";}
 async function convert(){if(!file||busy)return;setBusy(true);setStatus("PDF/A-2b로 변환하고 veraPDF로 적합성을 검사 중입니다…");try{const response=await postDocument("pdfa",file);downloadDocument(await response.blob(),file.name.replace(/\.pdf$/i,"")+"-pdfa-2b.pdf");setStatus("완료: veraPDF의 PDF/A-2b 검사를 통과했습니다. 결과 파일의 글꼴과 배치도 확인하세요.");}catch(e){setStatus(e instanceof Error?e.message:"변환하지 못했습니다.");}finally{setBusy(false);}}
 return <section className="tool-content">{dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아주세요</div>}<h1>PDF PDF/A로 변환</h1><h2>장기 보관용 PDF/A-2b로 변환하고 적합성을 검사합니다.</h2><div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={select}/></label></div><p className="tool-drop">또는 파일을 화면에 놓아 가져오기</p><div className="tool-work"><p>25MB·100쪽 이하. 이 PC의 LibreOffice로 변환한 뒤 veraPDF 검사를 통과한 파일만 제공합니다. 원본 서명·양식·첨부파일 등 상호작용 기능은 보존되지 않을 수 있으며, 글꼴·배치가 달라질 수 있습니다. 원본은 보존됩니다.</p><p>변환 과정에서 이 PC의 임시 폴더를 사용하고 작업이 끝나면 삭제합니다. PDF/A-1·3·4는 현재 지원하지 않습니다.</p>{file&&<><p>{file.name}</p><button className="tool-run" disabled={busy} onClick={convert}>{busy?"변환·검사 중…":"PDF/A-2b 변환 및 검사"}</button></>}<p role="status">{status}</p></div></section>;
}
