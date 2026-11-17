"use client";
import {useState, type ChangeEvent} from "react";
import {useFileDrop} from "./use-file-drop";
import {validateFiles} from "./file-drop";
import {serviceAddress} from "./service-address";
type Operation="protect"|"unlock"|"compress"|"word"|"powerpoint"|"repair";
const labels={protect:{title:"PDF 보호",description:"PDF 열기 암호를 설정합니다 (AES-256).",action:"암호 설정하기",name:"protected.pdf"},unlock:{title:"PDF 잠금해제",description:"현재 암호를 입력해 PDF의 열기 암호를 제거합니다.",action:"잠금해제하기",name:"unlocked.pdf"},compress:{title:"PDF 압축",description:"문서와 이미지 품질을 유지하며 PDF를 무손실 최적화합니다.",action:"PDF 최적화하기",name:"optimized.pdf"},word:{title:"PDF 워드 변환",description:"PDF의 텍스트·표·이미지를 편집 가능한 Word 문서로 변환합니다.",action:"Word로 변환",name:"converted.docx"},powerpoint:{title:"PDF 파워포인트 변환",description:"PDF 페이지를 이미지 슬라이드로 담은 PowerPoint를 만듭니다.",action:"PowerPoint로 변환",name:"converted.pptx"},repair:{title:"PDF 복구",description:"읽을 수 있는 손상 PDF를 다시 저장해 구조 오류 복구를 시도합니다.",action:"PDF 복구 시도",name:"repaired.pdf"}};
export default function LocalPdfTool({operation}:{operation:Operation}){
 const info=labels[operation];
 const [file,setFile]=useState<File|null>(null),[password,setPassword]=useState(""),[confirm,setConfirm]=useState(""),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하의 PDF를 선택하세요.");return;}setFile(files[0]);setPassword("");setConfirm("");setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function run(){
  if(!file||busy)return;
  if(operation==="protect"&&(!password||password!==confirm)){setStatus("암호와 암호 확인을 동일하게 입력하세요.");return;}
  setBusy(true);setStatus("이 PC의 로컬 PDF 서비스에서 처리 중…");
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),(operation==="word"||operation==="powerpoint")?600000:120000);
  try{
   const encoded=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=()=>reject(new Error("파일을 읽지 못했습니다."));reader.readAsDataURL(file);});
   const response=await fetch(`${serviceAddress("pdf")}/api/pdf/${operation}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({pdf:encoded,password}),signal:controller.signal,cache:"no-store"});
   if(!response.ok){const error=await response.json();throw new Error(error.error||"PDF 처리에 실패했습니다.");}
   const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=info.name;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
   setPassword("");setConfirm("");
   setStatus(operation==="word"&&response.headers.get("X-Conversion-Mode")==="text-only"?"완료: OCR 글자를 편집 가능한 Word 텍스트로 저장했습니다. 원본 이미지·표·서식은 복원되지 않았습니다.":operation==="compress"?(blob.size<file.size?`완료: ${file.size.toLocaleString()} → ${blob.size.toLocaleString()}바이트 (${((1-blob.size/file.size)*100).toFixed(1)}% 감소).`:"이미 최적화된 PDF입니다. 크기를 늘리지 않고 원본을 다운로드했습니다."):"완료했습니다. 다운로드한 PDF를 확인하세요.");
  }catch(e){setStatus(e instanceof TypeError?"로컬 PDF 서비스에 연결하지 못했습니다. 프로젝트의 start-pdf-service.cmd를 실행하세요.":e instanceof Error&&e.name==="AbortError"?"처리 시간이 초과되었습니다. 더 작은 파일로 다시 시도하세요.":e instanceof Error?e.message:"PDF 처리에 실패했습니다.");}
  finally{clearTimeout(timeout);setBusy(false);}
 }
 return <section className="tool-content">
  {dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 화면에 놓으세요</div>}
  <h1>{info.title}</h1><h2>{info.description}</h2>
  <div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={select}/></label></div><p className="tool-drop">또는 PDF를 화면에 놓아 가져오기</p>
  <div className="tool-work"><p>최대 25MB. 공유 링크에서는 파일과 암호가 HTTPS를 통해 운영자의 PC로 전송되어 처리됩니다. 처리용 파일은 보관함에 자동 저장하지 않습니다. 전자서명 문서는 재저장 시 서명 유효성이 바뀔 수 있습니다.</p>
   {operation==="compress"&&<p>이미지 해상도를 낮추지 않습니다. 문서에 따라 크기가 줄지 않을 수 있습니다.</p>}
   {operation==="repair"&&<p>삭제된 내용·비밀번호를 복원하지 않습니다. 심하게 손상된 파일은 복구되지 않을 수 있습니다.</p>}{operation==="powerpoint"&&<p>100쪽까지 지원합니다. 각 페이지를 이미지로 저장하므로 슬라이드의 글자를 직접 편집할 수 없습니다.</p>}{operation==="word"&&<p>200쪽까지 지원합니다. 복잡한 배치·글꼴·수식은 원본과 다를 수 있습니다. 스캔 문서는 먼저 OCR PDF를 사용하세요. OCR 텍스트층은 텍스트 위주의 Word로 변환될 수 있습니다.</p>}
   {file&&<><p>{file.name}</p>{(operation==="protect"||operation==="unlock")&&<label>{operation==="protect"?"새 PDF 암호":"현재 PDF 암호"}<input type="password" value={password} autoComplete="off" disabled={busy} onChange={e=>setPassword(e.target.value)}/></label>}{operation==="protect"&&<label>암호 확인<input type="password" autoComplete="off" value={confirm} disabled={busy} onChange={e=>setConfirm(e.target.value)}/></label>}<button className="tool-run" disabled={busy} onClick={run}>{busy?"처리 중…":info.action}</button></>}
   <p role="status">{status}</p>
  </div>
 </section>;
}
