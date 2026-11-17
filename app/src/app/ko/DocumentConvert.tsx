"use client";
import {useState,type ChangeEvent} from "react";
import {useFileDrop} from "./use-file-drop";
import {validateFiles} from "./file-drop";
import {postDocument,downloadDocument} from "./local-api";
type Kind="docx"|"xlsx"|"pptx"|"translate";
const titles={docx:"Word PDF로 변환",xlsx:"Excel PDF로 변환",pptx:"파워포인트 PDF로 변환",translate:"PDF 번역"};
export default function DocumentConvert({kind}:{kind:Kind}){
 const translate=kind==="translate",accept=translate?".pdf,application/pdf":"."+kind;
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState(""),[target,setTarget]=useState("ko");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,accept,false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하의 파일을 선택하세요.");return;}setFile(files[0]);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function select(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function run(){if(!file||busy)return;setBusy(true);setStatus(translate?"로컬 Qwen 모델이 번역하고 있습니다. 긴 문서는 수 분 걸릴 수 있습니다…":"로컬 Office 엔진에서 PDF를 만드는 중…");try{const response=await postDocument(translate?"translate":"office",file,translate?{target}:{extension:kind});downloadDocument(await response.blob(),file.name.replace(/\.[^.]+$/,"")+(translate?"-translated.pdf":".pdf"));setStatus("완료했습니다. PDF를 다운로드했습니다. 원본과 결과를 대조해 확인하세요.");}catch(e){setStatus(e instanceof Error?e.message:"변환에 실패했습니다.");}finally{setBusy(false);}}
 return <section className="tool-content">{dragging&&<div className="file-drop-overlay" role="status">파일을 놓아주세요</div>}<h1>{titles[kind]}</h1><h2>{translate?"로컬 AI로 문서 텍스트를 번역해 새 PDF를 만듭니다.":`${kind.toUpperCase()} 문서를 로컬에서 PDF로 변환합니다.`}</h2>
 <div className="tool-picker"><label className="tool-file-button">파일 선택<input type="file" accept={accept} disabled={busy} onChange={select}/></label></div><p className="tool-drop">또는 파일을 화면에 놓아 가져오기</p>
 <div className="tool-work">{translate?<><p>20쪽·추출 텍스트 12,000자까지 지원합니다. 번역 결과는 텍스트 PDF이며 원본 표·그림·페이지 배치를 보존하지 않습니다. AI 번역에는 오류·누락이 있을 수 있습니다. 스캔 문서는 먼저 OCR을 사용하세요. 파일은 이 PC에서만 처리됩니다.</p><label>번역할 언어<select disabled={busy} value={target} onChange={e=>setTarget(e.target.value)}><option value="ko">한국어</option><option value="en">영어</option></select></label></>:<p>최대 25MB. 매크로·외부 파일 연결 문서는 지원하지 않습니다. 문서는 이 PC의 임시 작업 폴더에서 변환 후 삭제합니다. 글꼴·인쇄 영역·페이지 나눔은 원본과 다를 수 있습니다. 구형 DOC·XLS·PPT는 최신 형식으로 저장해 주세요.</p>}
 {file&&<><p>{file.name}</p><button className="tool-run" disabled={busy} onClick={run}>{busy?"처리 중…":translate?"번역 PDF 만들기":"PDF로 변환"}</button></>}<p role="status">{status}</p></div></section>;
}
